from django.db import migrations


def force_imported_events_published(apps, schema_editor):
    Acte = apps.get_model("agenda", "Acte")
    Acte.objects.exclude(external_source="").update(estat="PUBLICAT")


class Migration(migrations.Migration):
    dependencies = [
        ("agenda", "0006_acte_es_important_and_external_type"),
    ]

    operations = [
        migrations.RunPython(force_imported_events_published, migrations.RunPython.noop),
    ]
