from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('agenda', '0006_acte_es_important_and_external_type'),
        ('reunions', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='reunio',
            name='acte_agenda',
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=models.SET_NULL,
                related_name='reunio_relacionada',
                to='agenda.acte',
            ),
        ),
    ]
