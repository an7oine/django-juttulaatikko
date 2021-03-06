# Generated by Django 3.1.6 on 2021-02-19 15:30

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Juttu',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ],
        ),
        migrations.CreateModel(
            name='Viesti',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('aika', models.DateTimeField(auto_now_add=True, verbose_name='aika')),
                ('teksti', models.TextField(verbose_name='teksti')),
                ('juttu', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='viestit', to='juttulaatikko.juttu', verbose_name='juttu')),
                ('kirjoittaja', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='kirjoittaja')),
            ],
        ),
        migrations.CreateModel(
            name='Juttelija',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('anonyymi', models.CharField(blank=True, max_length=40, verbose_name='anonyymi')),
                ('juttu', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='juttelijat', to='juttulaatikko.juttu', verbose_name='juttu')),
                ('kayttaja', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='käyttäjä')),
            ],
        ),
    ]
