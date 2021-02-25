# -*- coding: utf-8 -*-

from asgiref.sync import sync_to_async

from .juttulaatikko import Juttulaatikko


class KasikirjoitettuJuttulaatikko(Juttulaatikko):

  @property
  def kasikirjoitettu_kirjoittaja_id(self):
    raise NotImplementedError

  async def kasikirjoitus(self, laheta):
    raise NotImplementedError

  async def tallenna_uusi_viesti(
    self, *, teksti, kirjoittaja_id, ohita_kasikirjoitus=False
  ):
    viesti = await super().tallenna_uusi_viesti(
      kirjoittaja_id, teksti
    )
    if not ohita_kasikirjoitus:
      try:
        await self._kasikirjoitus.asend((
          kirjoittaja_id == self.kayttaja_id,
          teksti,
        ))
      except StopAsyncIteration:
        pass
    return viesti
    # async def tallenna_uusi_viesti


  async def websocket(self, request, *args, **kwargs):
    automaattikayttaja_id = await sync_to_async(
      lambda: self.kasikirjoitettu_kirjoittaja_id
    )()
    self._kasikirjoitus = self.kasikirjoitus(
      lambda teksti: self.tallenna_uusi_viesti(
        teksti=teksti,
        kirjoittaja_id=automaattikayttaja_id,
        ohita_kasikirjoitus=True
      )
    )
    await self._kasikirjoitus.asend(None)
    return await super().websocket(request, *args, **kwargs)
    # async def websocket

  # class KasikirjoitettuJuttulaatikko
