# -*- coding: utf-8 -*-

import asyncio

from asgiref.sync import async_to_sync, sync_to_async

from django.utils.functional import cached_property
from django.views import generic

from pistoke.nakyma import WebsocketNakyma
from pistoke.tyokalut import csrf_tarkistus, json_viestiliikenne

from juttulaatikko.celery import celery_app
from juttulaatikko import mallit


class HaeTaiLuoSaate(generic.detail.SingleObjectMixin):
  # pylint: disable=no-member

  def get_object(self, queryset=None):
    if self._uusi:
      return self.model.objects.create()
    else:
      return super().get_object(queryset=queryset)
    # def get_object

  @cached_property
  def _uusi(self):
    return not self.kwargs.get(self.pk_url_kwarg) \
    and not self.kwargs.get(self.slug_url_kwarg)
    # def _uusi

  # class HaeTaiLuoSaate


class Viestisaate:
  # pylint: disable=no-member

  def _aiemmat_viestit(self):
    # pylint: disable=attribute-defined-outside-init
    return list(self.object.viestit.all())
    # def _aiemmat_viestit

  def _tallenna_uusi_viesti(self, kirjoittaja_id, teksti):
    return mallit.Viesti.objects.create(
      teksti=teksti,
      juttu_id=self.object.pk,
      kirjoittaja_id=kirjoittaja_id,
    )
    # def _tallenna_uusi_viesti

  async def _laheta_aiemmat_viestit(self):
    for viesti in await sync_to_async(self._aiemmat_viestit)():
      await self.request.send(viesti.kayttajalle(self.kayttaja_id))
    # async def _laheta_aiemmat_viestit

  async def _laheta_uusi_viesti(self, viesti):
    await self.request.send(viesti.kayttajalle(self.kayttaja_id))
    # async def _laheta_uusi_viesti

  # class Viestisaate


class CeleryViestisaate(Viestisaate):
  # pylint: disable=no-member

  @cached_property
  def _celery_valittaja(self):
    return celery_app.broker_connection().channel()
    # def _celery_valittaja

  @cached_property
  def _celery_viestikanava(self):
    return f'juttulaatikko.viesti.{self.object.pk}'
    # def _celery_viestikanava

  @cached_property
  def _celery_lahetys(self):
    return celery_app.events.Dispatcher(channel=self._celery_valittaja)
    # def _celery_lahetys

  @cached_property
  def _celery_vastaanotto(self):
    return celery_app.events.Receiver(channel=self._celery_valittaja, handlers={
      self._celery_viestikanava: async_to_sync(
        lambda signaali: self._laheta_uusi_viesti(
          mallit.Viesti.celery_signaalista(signaali)
        )
      ),
    })
    # def _celery_vastaanotto

  async def tallenna_uusi_viesti(self, kirjoittaja_id, teksti):
    viesti = await sync_to_async(
      self._tallenna_uusi_viesti
    )(kirjoittaja_id, teksti)
    self._celery_lahetys.send(
      type=self._celery_viestikanava,
      **viesti.celery_signaaliksi(),
    )
    return viesti
    # async def tallenna_uusi_viesti

  # class CeleryViestisaate


class Juttulaatikko(
  HaeTaiLuoSaate,
  CeleryViestisaate,
  WebsocketNakyma,
):
  model = mallit.Juttu

  @property
  def kayttaja_id(self):
    return getattr(self.request.user, 'id', None)
    # def kayttaja_id

  async def aloita_uusi_juttu(self):
    # pylint: disable=attribute-defined-outside-init
    # Odotetaan ensimmäistä viestiä.
    # Huomaa, että mikäli yhteys katkeaa ennen kuin yhtään viestiä
    # on vastaanotettu, viestiketjua ei luoda.
    teksti = (await self.request.receive()).get('teksti')
    self.object = await sync_to_async(self.get_object)()
    await self.tallenna_uusi_viesti(
      teksti=teksti,
      kirjoittaja_id=self.kayttaja_id,
    )
    # async def aloita_uusi_juttu

  async def jatka_aiempaa_juttua(self):
    # pylint: disable=attribute-defined-outside-init
    self.object = await sync_to_async(self.get_object)()
    # async def jatka_aiempaa_juttua

  async def viestien_kirjoitus(self):
    ''' Käyttäjän kirjoittaminen viestien käsittely. '''
    while True:
      teksti = (await self.request.receive()).get('teksti')
      await self.tallenna_uusi_viesti(
        teksti=teksti,
        kirjoittaja_id=self.kayttaja_id,
      )
      # while True
    # async def kirjoitus

  @json_viestiliikenne
  @csrf_tarkistus(csrf_avain='csrfmiddlewaretoken', virhe_avain='teksti')
  async def websocket(self, request, *args, **kwargs):
    # Luo tai nouda pyydetty juttu.
    if self._uusi:
      await self.aloita_uusi_juttu()
    else:
      await self.jatka_aiempaa_juttua()

    # Kuuntele Celery-signaaleja ja välitä viestit käyttäjälle.
    loop = asyncio.get_running_loop()
    luku = loop.run_in_executor(None, self._celery_vastaanotto.capture)

    # Lähetetään aiemmat viestit, ml. käyttäjän oma, ensimmäinen
    # viesti, mikäli viestiketju on uusi.
    await self._laheta_aiemmat_viestit()

    # Lue viestejä käyttäjältä, kunnes yhteys katkaistaan.
    # Katkaise sitten Celery-viestien vastaanotto.
    try:
      await self.viestien_kirjoitus()
    finally:
      self._celery_vastaanotto.should_stop = True
      await luku
    # async def websocket

  # class Juttulaatikko
