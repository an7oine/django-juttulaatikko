# -*- coding: utf-8 -*-

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.fields import GenericForeignKey
from django.db import models
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
  # class Viesti
