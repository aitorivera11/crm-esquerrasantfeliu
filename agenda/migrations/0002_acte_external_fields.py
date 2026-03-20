from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('agenda', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='acte',
            name='external_id',
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name='acte',
            name='external_source',
            field=models.CharField(blank=True, max_length=50),
        ),
        migrations.AddField(
            model_name='acte',
            name='source_checksum',
            field=models.CharField(blank=True, max_length=64),
        ),
        migrations.AddField(
            model_name='acte',
            name='source_payload',
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name='acte',
            name='source_url',
            field=models.URLField(blank=True),
        ),
        migrations.AddConstraint(
            model_name='acte',
            constraint=models.UniqueConstraint(fields=('external_source', 'external_id'), name='agenda_unique_external_source_id'),
        ),
    ]
