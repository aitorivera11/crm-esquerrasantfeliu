from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('agenda', '0010_acte_imatge'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='participacioacte',
            unique_together=set(),
        ),
        migrations.AddConstraint(
            model_name='participacioacte',
            constraint=models.UniqueConstraint(
                fields=['usuari', 'acte'],
                name='agenda_unique_participacio_usuari_acte',
            ),
        ),
    ]
