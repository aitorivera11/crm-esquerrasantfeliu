from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='Persona',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('creat_el', models.DateTimeField(auto_now_add=True)),
                ('actualitzat_el', models.DateTimeField(auto_now=True)),
                ('nom', models.CharField(max_length=255)),
                ('email', models.EmailField(blank=True, max_length=254)),
                ('telefon', models.CharField(blank=True, max_length=20)),
                ('notes', models.TextField(blank=True)),
            ],
            options={
                'verbose_name': 'persona',
                'verbose_name_plural': 'persones',
                'ordering': ['nom'],
            },
        ),
    ]
