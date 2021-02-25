# -*- coding: utf-8 -*-

from django.contrib.auth import get_user_model
from django.urls import path
from django.utils.decorators import method_decorator
from django.views.decorators.clickjacking import (
  xframe_options_exempt,
)
from django.views.decorators.csrf import csrf_exempt

from juttulaatikko.nakyma import Juttunakyma
from juttulaatikko.kasikirjoitus import KasikirjoitettuJuttulaatikko


@method_decorator(xframe_options_exempt, name='get')
@method_decorator(csrf_exempt, name='websocket')
class Demolaatikko(KasikirjoitettuJuttulaatikko, Juttunakyma):
  template_name = 'juttu/demo.html'

  tervetulotoivotus = {
    'teksti': 'Hei! Kuinka voin auttaa?'
  }
  virheviesti = {
    'teksti': 'Juttua ei löydy!'
  }

  @property
  def kasikirjoitettu_kirjoittaja_id(self):
    return get_user_model().objects.first().pk

  def get_queryset(self):
    if self.request.user.is_superuser:
      return self.model.objects.all()
    else:
      return super().get_queryset()
    # def get_queryset

  async def aloita_uusi_juttu(self):
    await self.request.send(self.tervetulotoivotus)
    return await super().aloita_uusi_juttu()
    # async def aloita_uusi_juttu

  async def jatka_aiempaa_juttua(self):
    try:
      return await super().jatka_aiempaa_juttua()
    except self.model.DoesNotExist:
      await self.request.send(self.virheviesti)
      raise
    # async def jatka_aiempaa_juttua

  async def kasikirjoitus(self, laheta):
    while True:
      kayttajalta, viesti = yield
      if 'Terve' in viesti:
        await laheta(', maailma!')
    # async def kasikirjoitus

  # class Demolaatikko


urlpatterns = [
  path('', Demolaatikko.as_view(), name='demo'),
  path('<str:pk>/', Demolaatikko.as_view(), name='demo'),
]
