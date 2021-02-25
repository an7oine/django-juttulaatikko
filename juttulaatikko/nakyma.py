# -*- coding: utf-8 -*-

from asgiref.sync import sync_to_async

from django.core.exceptions import ImproperlyConfigured
from django.http import Http404
from django.utils.crypto import get_random_string
from django.utils.functional import cached_property
from django.views import generic

from juttulaatikko.juttulaatikko import Juttulaatikko


class Juttunakyma(Juttulaatikko, generic.TemplateView):
  template_name = 'juttulaatikko.html'

  @cached_property
  def anonyymi(self):
    return self.request.COOKIES.get('juttulaatikko_anonyymi')

  @property
  def juttelija(self):
    return self.object.juttelijat.get(**(
      {'kayttaja': self.request.user}
      if self.request.user.is_authenticated
      else {'anonyymi': self.anonyymi}
    ))

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
    juttu = super().get_object(queryset=queryset)
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

  async def websocket(self, request, *args, **kwargs):
    # Poista käyttäjä keskustelusta yhteyden katkettua.
    try:
      await super().websocket(request, *args, **kwargs)
    finally:
      await sync_to_async(
        # pylint: disable=unnecessary-lambda
        lambda: self.juttelija.delete()
      )()
    # async def websocket

  def get(self, request, *args, **kwargs):
    # pylint: disable=attribute-defined-outside-init

    # Varmista, että Websocket-yhteys on käytettävissä.
    if not getattr(request, 'websocket', False):
      raise ImproperlyConfigured('Websocket-yhteys ei ole käytettävissä!')

    # Varmista, että pyydetty, olemassaoleva Juttu on olemassa.
    # Huomaa, että uutta Juttua ei luoda GET-pyynnöllä.
    # Vrt. `generic.BaseDetailView`.
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
    # `juttulaatikko_anonyymi`-eväste parametrillä `SameSite=none`,
    # jotta istunto voidaan myöhemmin yksilöidä.
    if not self.request.user.is_authenticated:
      vastaus.set_cookie(
        'juttulaatikko_anonyymi',
        get_random_string(length=32),
        max_age=None, expires=None,
        path=request.path,
        secure=request.is_secure(),
        samesite='none',
      )
    return vastaus
    # def get

  # class Juttunakyma
