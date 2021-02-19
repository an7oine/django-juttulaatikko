# -*- coding: utf-8 -*-

import asyncio
import functools
import json

from asgiref.sync import async_to_sync, sync_to_async

from django.core.exceptions import ImproperlyConfigured
from django.http import Http404
from django.utils.crypto import get_random_string
from django.utils.functional import cached_property
from django.views import generic

from pistoke.nakyma import WebsocketNakyma

from juttulaatikko.celery import celery_app
from juttulaatikko import mallit


class Juttu(generic.detail.SingleObjectMixin):
  model = mallit.Juttu
  request = None
  kwargs = None

  @cached_property
  def anonyymi(self):
    return self.request.COOKIES.get('juttulaatikko_anonyymi')

  def get_queryset(self):
    qs = super().get_queryset()
    if self.request.user.is_authenticated:
      return qs.filter(
        juttelijat__kayttaja=self.request.user,
      )
    else:
      return qs.filter(
        juttelijat__anonyymi=self.anonyymi,
      )
    # def get_queryset

  def get_object(self, queryset=None):
    try:
      juttu = super().get_object(queryset=queryset)
    except AttributeError:
      juttu = self.model.objects.create()
    if self.request.user.is_authenticated:
      juttu.juttelijat.get_or_create(
        kayttaja=self.request.user,
      )
    else:
      juttu.juttelijat.get_or_create(
        anonyymi=self.anonyymi,
      )
    return juttu
    # def get_object

  @cached_property
  def _uusi(self):
    return not self.kwargs.get(self.pk_url_kwarg) \
    and not self.kwargs.get(self.slug_url_kwarg)
    # def _uusi

  # class Juttu


class Viesti:
  request = None
  object = None

  def viestin_tiedot(self, viesti):
    return {
      'id': int(viesti.id),
      'juttu_id': int(viesti.juttu_id),
      'aika': viesti.aika.strftime('%-d.%-m.%Y klo %-H.%M'),
      'kirjoittaja': str(viesti.kirjoittaja),
      'teksti': viesti.teksti,
      'oma': viesti.kirjoittaja == self.request.user or (
        viesti.kirjoittaja is None and not self.request.user.is_authenticated
      ),
    }
    # def viestin_tiedot

  def _aiemmat_viestit(self):
    # pylint: disable=attribute-defined-outside-init
    return [
      self.viestin_tiedot(viesti)
      for viesti in self.object.viestit.all()
    ]
    # def _aiemmat_viestit

  def _tallenna_viesti(self, teksti):
    return self.object.viestit.create(
      kirjoittaja=(
        self.request.user
        if self.request.user.is_authenticated
        else None
      ),
      teksti=teksti,
    )
    # def _tallenna_viesti

  async def _laheta_aiemmat_viestit(self):
    for viesti in await sync_to_async(self._aiemmat_viestit)():
      await self.request.send(viesti)
    # async def _laheta_aiemmat_viestit

  async def _laheta_uusi_viesti(self, viesti):
    await self.request.send(viesti)
    # async def _laheta_uusi_viesti

  # class Viesti


class Celery(Viesti):
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
        self._laheta_uusi_viesti
      ),
    })
    # def _celery_vastaanotto

  def _tallenna_viesti(self, teksti):
    viesti = super()._tallenna_viesti(teksti)
    self._celery_lahetys.send(
      type=self._celery_viestikanava,
      **self.viestin_tiedot(viesti),
    )
    # def _tallenna_viesti

  # class Celery


class Websocket(Celery, Viesti, Juttu, WebsocketNakyma):

  async def aloita_uusi_juttu(self, request):
    # pylint: disable=attribute-defined-outside-init
    # Odotetaan ensimmäistä viestiä.
    # Huomaa, että mikäli yhteys katkeaa ennen kuin yhtään viestiä
    # on vastaanotettu, viestiketjua ei luoda.
    teksti = await request.receive()
    self.object = await sync_to_async(self.get_object)()
    await sync_to_async(self._tallenna_viesti)(teksti)
    # async def aloita_uusi_juttu

  async def jatka_aiempaa_juttua(self, request):
    # pylint: disable=attribute-defined-outside-init
    self.object = await sync_to_async(self.get_object)()
    # async def jatka_aiempaa_juttua

  async def websocket(self, request, *args, **kwargs):
    '''
    Poimi CSRF-tunniste ensimmäisestä sanomasta ja tarkista se.
    '''
    # pylint: disable=arguments-differ, unused-argument

    # Websocket-kättely.
    kattely = await request.receive()
    try:
      kattely = json.loads(kattely)
    except ValueError:
      return await request.send(
        'Yhteyden muodostus epäonnistui!'
      )

    # Tarkista kättelytiedoissa annettu CSRF-avain, ellei
    # `method_decorator(csrf_exempt)` ole käytössä.
    if not getattr(getattr(self, 'websocket'), 'csrf_exempt', False) \
    and not request.tarkista_csrf(kattely.get('csrfmiddlewaretoken')):
      return await request.send(
        'CSRF-avain puuttuu tai se on virheellinen!'
      )

    # Lähetä kaikki sanomat JSON-muodossa.
    @functools.wraps(request.send)
    async def send(viesti):
      return await send.__wrapped__(json.dumps(viesti))
    request.send = send

    # Luo tai nouda pyydetty juttu.
    if self._uusi:
      await self.aloita_uusi_juttu(request)
      assert self.object.pk
    else:
      await self.jatka_aiempaa_juttua(request)
      try: self.object
      except AttributeError: return

    # Kuuntele Celery-signaaleja ja välitä viestit käyttäjälle.
    loop = asyncio.get_running_loop()
    luku = loop.run_in_executor(None, self._celery_vastaanotto.capture)

    # Lähetetään aiemmat viestit, ml. käyttäjän oma, ensimmäinen
    # viesti, mikäli viestiketju on uusi.
    await self._laheta_aiemmat_viestit()

    async def kirjoitus():
      ''' Käyttäjän kirjoittaminen viestien käsittely. '''
      while True:
        await sync_to_async(self._tallenna_viesti)(
          await request.receive()
        )
        # while True
      # async def kirjoitus

    # Lue viestejä käyttäjältä, kunnes yhteys katkaistaan.
    # Katkaise sitten Celery-viestien vastaanotto.
    try:
      await kirjoitus()
    finally:
      self._celery_vastaanotto.should_stop = True
      await luku
      # Poista käyttäjä keskustelusta.
      await sync_to_async(
        lambda: self.object.juttelijat.get(**(
          {'kayttaja': self.request.user}
          if self.request.user.is_authenticated
          else {'anonyymi': self.anonyymi}
        )).delete()
      )()
    # async def websocket

  # class Websocket


class Juttulaatikko(Websocket, generic.TemplateView):
  template_name = 'juttulaatikko.html'

  def get(self, request, *args, **kwargs):
    # Varmista, että Websocket-yhteys on käytettävissä.
    if not getattr(request, 'websocket', False):
      raise ImproperlyConfigured('Websocket-yhteys ei ole käytettävissä!')

    # Varmista, että pyydetty, olemassaoleva keskustelu on saatavilla.
    if self._uusi:
      self.object = None
    else:
      try:
        self.object = self.get_object()
      except self.model.DoesNotExist as exc:
        raise Http404 from exc

    # Hae normaali HTML-vastaus.
    vastaus = super().get(request, *args, **kwargs)

    # Lähetä anonyymille keskustelijalle erillinen
    # `juttulaatikko_anonyymi`-eväste parametrillä `Same-Site: None`,
    # jotta istunto voidaan myöhemmin yksilöidä.
    if not self.request.user.is_authenticated:
      vastaus.set_cookie(
        'juttulaatikko_anonyymi',
        get_random_string(length=32),
        max_age=None, expires=None,
        path=request.path,
        secure=self.request.is_secure,
        samesite='none',
      )
    return vastaus
    # def get

  # class Juttulaatikko
