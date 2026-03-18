from django.contrib import admin

from .models import Auditoria


@admin.register(Auditoria)
class AuditoriaAdmin(admin.ModelAdmin):
    list_display = ('model_afectat', 'object_id', 'accio', 'usuari', 'creat_el')
    list_filter = ('accio', 'model_afectat')
    search_fields = ('model_afectat', 'object_id', 'usuari__username')
