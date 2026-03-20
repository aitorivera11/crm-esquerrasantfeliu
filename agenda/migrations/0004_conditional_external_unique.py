from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):
    dependencies = [
        ('agenda', '0003_actetipus_acte_aforament_acte_fi_acte_punt_trobada_and_more'),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name='acte',
            name='agenda_unique_external_source_id',
        ),
        migrations.AddConstraint(
            model_name='acte',
            constraint=models.UniqueConstraint(
                fields=('external_source', 'external_id'),
                condition=Q(external_source__gt='') & Q(external_id__gt=''),
                name='agenda_unique_external_source_id',
            ),
        ),
    ]
