from django.db import migrations, models


def assign_external_type(apps, schema_editor):
    Acte = apps.get_model("agenda", "Acte")
    ActeTipus = apps.get_model("agenda", "ActeTipus")
    external_type = ActeTipus.objects.filter(nom__iexact="Acte extern").first()
    if external_type:
        Acte.objects.filter(external_source__gt="").update(tipus=external_type)


class Migration(migrations.Migration):

    dependencies = [
        ("agenda", "0005_acte_entitats_relacionades_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="acte",
            name="es_important",
            field=models.BooleanField(default=False, help_text="Destaca l’acte a la llista i als resums clau."),
        ),
        migrations.RunPython(assign_external_type, migrations.RunPython.noop),
    ]
