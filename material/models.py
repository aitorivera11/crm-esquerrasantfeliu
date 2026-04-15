from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from core.models import TimeStampedModel


class CategoriaMaterial(TimeStampedModel):
    nom = models.CharField(max_length=120, unique=True)
    pare = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='fills')
    activa = models.BooleanField(default=True)

    class Meta:
        ordering = ['nom']
        verbose_name = 'categoria de material'
        verbose_name_plural = 'categories de material'

    def __str__(self):
        return self.nom


class UbicacioMaterial(TimeStampedModel):
    nom = models.CharField(max_length=150, unique=True)
    adreca = models.CharField(max_length=255, blank=True)
    notes = models.TextField(blank=True)
    responsable_per_defecte = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='ubicacions_material_responsable',
    )
    activa = models.BooleanField(default=True)

    class Meta:
        ordering = ['nom']
        verbose_name = 'ubicació de material'
        verbose_name_plural = 'ubicacions de material'

    def __str__(self):
        return self.nom


class CompraMaterial(TimeStampedModel):
    class MetodePagament(models.TextChoices):
        EFECTIU = 'EFECTIU', 'Efectiu'
        TARGETA = 'TARGETA', 'Targeta'
        TRANSFERENCIA = 'TRANSFERENCIA', 'Transferència'
        BIZUM = 'BIZUM', 'Bizum'
        ALTRE = 'ALTRE', 'Altre'

    data_compra = models.DateField()
    proveidor = models.CharField(max_length=150)
    pagador_usuari = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='compres_material_pagades',
    )
    pagador_entitat = models.ForeignKey(
        'entitats.Entitat',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='compres_material_pagades',
    )
    cost_total = models.DecimalField(max_digits=10, decimal_places=2)
    metode_pagament = models.CharField(max_length=20, choices=MetodePagament.choices, default=MetodePagament.TARGETA)
    num_factura_ticket = models.CharField(max_length=80, blank=True)
    document = models.FileField(upload_to='material/compres/', blank=True)
    observacions = models.TextField(blank=True)

    class Meta:
        ordering = ['-data_compra', '-id']
        verbose_name = 'compra de material'
        verbose_name_plural = 'compres de material'

    def __str__(self):
        return f'Compra #{self.pk} - {self.proveidor}'


class LiniaCompraMaterial(TimeStampedModel):
    class TipusLinia(models.TextChoices):
        INVENTARIABLE = 'INVENTARIABLE', 'Inventariable'
        CONSUMIBLE = 'CONSUMIBLE', 'Consumible'

    compra = models.ForeignKey(CompraMaterial, on_delete=models.CASCADE, related_name='linies')
    categoria = models.ForeignKey(CategoriaMaterial, null=True, blank=True, on_delete=models.SET_NULL)
    tipus_linia = models.CharField(
        max_length=20,
        choices=TipusLinia.choices,
        default=TipusLinia.CONSUMIBLE,
    )
    descripcio = models.CharField(max_length=255)
    quantitat = models.PositiveIntegerField(default=1)
    preu_unitari = models.DecimalField(max_digits=10, decimal_places=2)
    iva_percent = models.DecimalField(max_digits=5, decimal_places=2, default=21)
    total_linia = models.DecimalField(max_digits=10, decimal_places=2)
    codi_barres = models.CharField(max_length=64, blank=True, db_index=True)
    foto = models.ImageField(upload_to='material/linies/', blank=True)

    class Meta:
        ordering = ['compra_id', 'id']
        verbose_name = 'línia de compra de material'
        verbose_name_plural = 'línies de compra de material'

    def __str__(self):
        return f'{self.descripcio} ({self.quantitat})'


class ItemMaterial(TimeStampedModel):
    class Estat(models.TextChoices):
        OPERATIU = 'OPERATIU', 'Operatiu'
        REPARACIO = 'REPARACIO', 'En reparació'
        BAIXA = 'BAIXA', 'Baixa'

    codi_intern = models.CharField(max_length=40, unique=True, db_index=True)
    descripcio = models.CharField(max_length=255)
    categoria = models.ForeignKey(CategoriaMaterial, null=True, blank=True, on_delete=models.SET_NULL)
    estat = models.CharField(max_length=20, choices=Estat.choices, default=Estat.OPERATIU)
    ubicacio_actual = models.ForeignKey(UbicacioMaterial, on_delete=models.PROTECT, related_name='items')
    data_alta = models.DateField()
    valor_estimad = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    codi_barres = models.CharField(max_length=64, blank=True, db_index=True)
    foto_principal = models.ImageField(upload_to='material/items/', blank=True)
    quantitat_actual = models.DecimalField(max_digits=12, decimal_places=2, default=1)
    linia_compra = models.OneToOneField(
        LiniaCompraMaterial,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='item_generat',
    )

    class Meta:
        ordering = ['codi_intern']
        verbose_name = 'ítem de material'
        verbose_name_plural = 'ítems de material'

    def __str__(self):
        return f'{self.codi_intern} · {self.descripcio}'


class StockMaterial(TimeStampedModel):
    producte = models.CharField(max_length=200)
    categoria = models.ForeignKey(CategoriaMaterial, null=True, blank=True, on_delete=models.SET_NULL)
    ubicacio = models.ForeignKey(UbicacioMaterial, on_delete=models.PROTECT, related_name='stocks')
    quantitat_actual = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    unitat = models.CharField(max_length=20, default='u')
    llindar_minim = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    codi_barres = models.CharField(max_length=64, blank=True, db_index=True)
    foto_principal = models.ImageField(upload_to='material/stocks/', blank=True)
    linia_compra = models.OneToOneField(
        LiniaCompraMaterial,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='stock_generat',
    )

    class Meta:
        ordering = ['producte']
        verbose_name = 'stock de material'
        verbose_name_plural = 'stocks de material'
        unique_together = ('producte', 'ubicacio')

    def clean(self):
        if self.quantitat_actual < 0:
            raise ValidationError({'quantitat_actual': 'La quantitat actual no pot ser negativa.'})

    def __str__(self):
        return f'{self.producte} ({self.quantitat_actual} {self.unitat})'


class MovimentMaterial(TimeStampedModel):
    class Tipus(models.TextChoices):
        ENTRADA = 'ENTRADA', 'Entrada'
        SORTIDA = 'SORTIDA', 'Sortida'
        TRASLLAT = 'TRASLLAT', 'Trasllat'
        AJUST = 'AJUST', 'Ajust'
        PRESTEC = 'PRESTEC', 'Préstec'
        DEVOLUCIO = 'DEVOLUCIO', 'Devolució'
        BAIXA = 'BAIXA', 'Baixa'

    tipus_moviment = models.CharField(max_length=20, choices=Tipus.choices)
    data_moviment = models.DateTimeField(auto_now_add=True)
    origen = models.ForeignKey(UbicacioMaterial, null=True, blank=True, on_delete=models.SET_NULL, related_name='moviments_sortida')
    desti = models.ForeignKey(UbicacioMaterial, null=True, blank=True, on_delete=models.SET_NULL, related_name='moviments_entrada')
    quantitat = models.DecimalField(max_digits=12, decimal_places=2, default=1)
    observacions = models.TextField(blank=True)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='moviments_material')
    item = models.ForeignKey(ItemMaterial, null=True, blank=True, on_delete=models.CASCADE, related_name='moviments')
    stock = models.ForeignKey(StockMaterial, null=True, blank=True, on_delete=models.CASCADE, related_name='moviments')

    class Meta:
        ordering = ['-data_moviment']
        verbose_name = 'moviment de material'
        verbose_name_plural = 'moviments de material'

    def __str__(self):
        return f'{self.get_tipus_moviment_display()} · {self.data_moviment:%d/%m/%Y %H:%M}'


class AssignacioMaterial(TimeStampedModel):
    class EstatReserva(models.TextChoices):
        RESERVAT = 'RESERVAT', 'Reservat'
        PREPARAT = 'PREPARAT', 'Preparat'
        RETORNAT = 'RETORNAT', 'Retornat'

    acte = models.ForeignKey('agenda.Acte', null=True, blank=True, on_delete=models.CASCADE, related_name='assignacions_material')
    tasca = models.ForeignKey('reunions.Tasca', null=True, blank=True, on_delete=models.CASCADE, related_name='assignacions_material')
    item = models.ForeignKey(ItemMaterial, null=True, blank=True, on_delete=models.CASCADE, related_name='assignacions')
    stock = models.ForeignKey(StockMaterial, null=True, blank=True, on_delete=models.CASCADE, related_name='assignacions')
    quantitat_reservada = models.DecimalField(max_digits=12, decimal_places=2, default=1)
    quantitat_retornada = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    estat_reserva = models.CharField(max_length=20, choices=EstatReserva.choices, default=EstatReserva.RESERVAT)

    class Meta:
        ordering = ['-creat_el']
        verbose_name = 'assignació de material'
        verbose_name_plural = 'assignacions de material'

    def clean(self):
        if not self.acte and not self.tasca:
            raise ValidationError('Cal vincular l’assignació a un acte o una tasca.')
        if self.acte and self.tasca:
            raise ValidationError('L’assignació només pot apuntar a un acte o a una tasca, no a tots dos.')
        if not self.item and not self.stock:
            raise ValidationError('Cal indicar un ítem o un stock de material.')

    def __str__(self):
        objectiu = self.acte or self.tasca
        return f'Assignació #{self.pk} · {objectiu}'
