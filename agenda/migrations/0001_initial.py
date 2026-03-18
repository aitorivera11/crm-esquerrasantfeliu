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
            name='Acte',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('creat_el', models.DateTimeField(auto_now_add=True)),
                ('actualitzat_el', models.DateTimeField(auto_now=True)),
                ('titol', models.CharField(max_length=255)),
                ('descripcio', models.TextField(blank=True)),
                ('inici', models.DateTimeField()),
                ('ubicacio', models.CharField(max_length=255)),
                ('estat', models.CharField(choices=[('ESBORRANY', 'Esborrany'), ('PUBLICAT', 'Publicat')], default='ESBORRANY', max_length=20)),
                ('creador', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='actes_creats', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['inici'],
                'permissions': [('can_view_participants', 'Pot veure participants'), ('can_mark_attendance', 'Pot marcar assistència real')],
            },
        ),
        migrations.CreateModel(
            name='ParticipacioActe',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('creat_el', models.DateTimeField(auto_now_add=True)),
                ('actualitzat_el', models.DateTimeField(auto_now=True)),
                ('intencio', models.CharField(choices=[('HI_ANIRE', 'Hi aniré'), ('POTSER', 'Potser'), ('NO_HI_ANIRE', 'No hi aniré')], max_length=20)),
                ('assistencia_real', models.CharField(choices=[('PENDENT', 'Pendent'), ('ASSISTEIX', 'Ha assistit'), ('NO_ASSISTEIX', 'No ha assistit')], default='PENDENT', max_length=20)),
                ('observacions', models.TextField(blank=True)),
                ('acte', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='participants', to='agenda.acte')),
                ('usuari', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='participacions_actes', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'participació a acte',
                'verbose_name_plural': 'participacions a actes',
                'ordering': ['usuari__nom_complet', 'usuari__username'],
                'unique_together': {('usuari', 'acte')},
            },
        ),
    ]
