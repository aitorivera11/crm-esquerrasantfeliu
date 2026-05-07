from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('material', '0004_itemmaterial_linia_compra_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='movimentmaterial',
            name='data_moviment',
        ),
    ]
