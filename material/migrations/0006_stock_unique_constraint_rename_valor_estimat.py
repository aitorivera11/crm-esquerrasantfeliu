from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('material', '0005_remove_movimentmaterial_data_moviment'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='stockmaterial',
            unique_together=set(),
        ),
        migrations.AddConstraint(
            model_name='stockmaterial',
            constraint=models.UniqueConstraint(
                fields=['producte', 'ubicacio'],
                name='material_unique_stock_producte_ubicacio',
            ),
        ),
        migrations.RenameField(
            model_name='itemmaterial',
            old_name='valor_estimad',
            new_name='valor_estimat',
        ),
    ]
