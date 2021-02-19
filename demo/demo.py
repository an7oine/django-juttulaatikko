# -*- coding: utf-8 -*-

from django.urls import path
from django.utils.decorators import method_decorator
from django.views.decorators.clickjacking import (
  xframe_options_exempt,
)
from django.views.decorators.csrf import csrf_exempt

from juttulaatikko.nakyma import Juttulaatikko


@method_decorator(xframe_options_exempt, name='get')
@method_decorator(csrf_exempt, name='websocket')
class Demolaatikko(Juttulaatikko):
  template_name = 'juttu/demo.html'

  tervetulotoivotus = {
    'teksti': 'Hei! Kuinka voin auttaa?'
  }
  virheviesti = {
    'teksti': 'Juttua ei löydy!'
  }

  async def aloita_uusi_juttu(self, request):
    await request.send(self.tervetulotoivotus)
    return await super().aloita_uusi_juttu(request)
    # async def aloita_uusi_juttu

  async def jatka_aiempaa_juttua(self, request):
    try:
      return await super().jatka_aiempaa_juttua(request)
    except self.malli.DoesNotExist:
      await request.send(self.virheviesti)
      raise
    # async def jatka_aiempaa_juttua

  # class Demolaatikko


urlpatterns = [
  path('', Demolaatikko.as_view(), name='demo'),
  path('<str:pk>/', Demolaatikko.as_view(), name='demo'),
]
