from django.contrib import admin

from .models import Candidatura, IntegrantLlista, PermisLlistaElectoral, PosicioLlista


@admin.register(Candidatura)
class CandidaturaAdmin(admin.ModelAdmin):
    list_display = ('nom', 'activa', 'creat_el', 'actualitzat_el')


@admin.register(IntegrantLlista)
class IntegrantLlistaAdmin(admin.ModelAdmin):
    list_display = ('nom_mostrat', 'candidatura', 'afiliacio', 'estat')
    list_filter = ('afiliacio', 'estat', 'candidatura')


@admin.register(PosicioLlista)
class PosicioLlistaAdmin(admin.ModelAdmin):
    list_display = ('numero', 'candidatura', 'integrant', 'es_titular')
    list_filter = ('candidatura',)


@admin.register(PermisLlistaElectoral)
class PermisLlistaElectoralAdmin(admin.ModelAdmin):
    list_display = ('user', 'creat_el')
