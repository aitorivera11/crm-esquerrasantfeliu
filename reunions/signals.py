from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from .models import HistoricEstatTasca, SeguimentTasca, Tasca, TascaRelacioReunio


@receiver(pre_save, sender=Tasca)
def preparar_canvi_estat_tasca(sender, instance, **kwargs):
    if instance.pk:
        instance._estat_anterior = sender.objects.filter(pk=instance.pk).values_list('estat', flat=True).first() or ''
    else:
        instance._estat_anterior = ''


@receiver(post_save, sender=Tasca)
def registrar_canvi_estat_tasca(sender, instance, created, **kwargs):
    if created:
        HistoricEstatTasca.objects.get_or_create(
            tasca=instance,
            estat_anterior='',
            estat_nou=instance.estat,
            canviat_per=instance.creada_per,
        )
        if instance.reunio_origen_id or instance.punt_acta_origen_id:
            TascaRelacioReunio.objects.get_or_create(
                tasca=instance,
                reunio=instance.reunio_origen or instance.punt_acta_origen.acta.reunio,
                punt_acta=instance.punt_acta_origen,
                punt_ordre_dia=instance.punt_acta_origen.punt_ordre_origen if instance.punt_acta_origen_id else None,
                tipus_relacio=TascaRelacioReunio.TipusRelacio.ORIGEN,
                defaults={'resum': 'Origen automàtic de la tasca a partir de la seva creació.'},
            )
        return

    previous = getattr(instance, '_estat_anterior', '')
    if previous and previous != instance.estat:
        HistoricEstatTasca.objects.create(tasca=instance, estat_anterior=previous, estat_nou=instance.estat)


@receiver(pre_save, sender=SeguimentTasca)
def aplicar_estat_des_de_seguiment(sender, instance, **kwargs):
    if instance.nou_estat and instance.tasca.estat != instance.nou_estat:
        HistoricEstatTasca.objects.create(
            tasca=instance.tasca,
            estat_anterior=instance.tasca.estat,
            estat_nou=instance.nou_estat,
            canviat_per=instance.autor,
            motiu=instance.comentari,
        )
        Tasca.objects.filter(pk=instance.tasca_id).update(estat=instance.nou_estat)
        instance.tasca.estat = instance.nou_estat
