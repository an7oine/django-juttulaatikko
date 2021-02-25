# -*- coding: utf-8 -*-

from datetime import datetime

from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class Juttu(models.Model):
  pass


class Juttelija(models.Model):
  juttu = models.ForeignKey(
    'Juttu',
    on_delete=models.CASCADE,
    related_name='juttelijat',
    verbose_name=_('juttu'),
  )
  kayttaja = models.ForeignKey(
    get_user_model(),
    on_delete=models.CASCADE,
    related_name='+',
    verbose_name=_('käyttäjä'),
    blank=True,
    null=True,
  )
  # Anonyymi.
  anonyymi = models.CharField(
    verbose_name=_('anonyymi'),
    max_length=40,
    blank=True,
  )
  # class Juttelija


class Viesti(models.Model):
  juttu = models.ForeignKey(
    'Juttu',
    on_delete=models.CASCADE,
    related_name='viestit',
    verbose_name=_('juttu'),
  )
  kirjoittaja = models.ForeignKey(
    get_user_model(),
    on_delete=models.SET_NULL,
    related_name='+',
    verbose_name=_('kirjoittaja'),
    blank=True,
    null=True,
  )
  aika = models.DateTimeField(
    _('aika'),
    auto_now_add=True,
  )
  teksti = models.TextField(
    _('teksti'),
  )

  @classmethod
  def celery_signaalista(cls, signaali):
    return cls(
      id=signaali.get('id'),
      juttu_id=signaali.get('juttu_id'),
      kirjoittaja_id=signaali.get('kirjoittaja_id'),
      teksti=signaali.get('teksti'),
      aika=datetime.fromtimestamp(signaali.get('aika')),
    )
    # def celery_signaalista

  def celery_signaaliksi(self):
    return {
      'id': self.id,
      'juttu_id': self.juttu_id,
      'kirjoittaja_id': self.kirjoittaja_id,
      'teksti': self.teksti,
      'aika': self.aika.timestamp(),
    }
    # def celery_signaaliksi

  @classmethod
  def kayttajalta(cls, teksti, juttu_id, kayttaja_id):
    return cls(
      juttu_id=int(juttu_id),
      kirjoittaja_id=kayttaja_id,
      aika=timezone.now(),
      teksti=teksti,
    )
    # def kayttajalta

  def kayttajalle(self, kayttaja_id):
    return {
      'id': self.id,
      'juttu_id': self.juttu_id,
      'kirjoittaja_id': self.kirjoittaja_id,
      'aika': self.aika.strftime('%-d.%-m.%Y klo %-H.%M'),
      'teksti': self.teksti,
      'oma': self.kirjoittaja_id == kayttaja_id,
    }
    # def kayttajalle

  # class Viesti
