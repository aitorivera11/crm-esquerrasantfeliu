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
            name='Auditoria',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('creat_el', models.DateTimeField(auto_now_add=True)),
                ('actualitzat_el', models.DateTimeField(auto_now=True)),
                ('accio', models.CharField(choices=[('CREATE', 'Creació'), ('UPDATE', 'Actualització'), ('DELETE', 'Eliminació'), ('STATUS', "Canvi d'estat")], max_length=20)),
                ('model_afectat', models.CharField(max_length=100)),
                ('object_id', models.CharField(max_length=50)),
                ('dades', models.JSONField(blank=True, default=dict)),
                ('usuari', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='auditories', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'auditoria',
                'verbose_name_plural': 'auditories',
                'ordering': ['-creat_el'],
            },
        ),
    ]
