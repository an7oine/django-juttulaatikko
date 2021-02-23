# -*- coding: utf-8 -*-

from celery.app import app_or_default

celery_app = app_or_default()
celery_app.config_from_object('django.conf:settings', namespace='CELERY')
