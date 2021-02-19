# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

setup(
  setup_requires='git-versiointi',
  name='django-juttulaatikko',
  description='Websocket-pohjainen Django-juttulaatikko',
  url='https://github.com/an7oine/django-juttulaatikko.git',
  author='Antti Hautaniemi',
  author_email='antti.hautaniemi@me.com',
  packages=['juttulaatikko'],
  include_package_data=True,
  entry_points={
    'django.sovellus': ['juttulaatikko = juttulaatikko'],
  },
  install_requires=['django-pistoke'],
)
