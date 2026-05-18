from django.contrib import admin

from .models import BlocPrograma, ComentariProposta, IdeaPluja, IdeaPublica, Proposta


@admin.register(BlocPrograma)
class BlocProgramaAdmin(admin.ModelAdmin):
    list_display = ('titol', 'pare', 'ordre', 'estat', 'creat_per')
    list_filter = ('estat', 'pare')
    search_fields = ('titol',)


@admin.register(Proposta)
class PropostaAdmin(admin.ModelAdmin):
    list_display = ('titol', 'bloc', 'estat', 'creat_per', 'creat_el')
    list_filter = ('estat', 'bloc')
    search_fields = ('titol', 'contingut')


@admin.register(ComentariProposta)
class ComentariPropostaAdmin(admin.ModelAdmin):
    list_display = ('proposta', 'autor', 'creat_el')
    search_fields = ('text',)


@admin.register(IdeaPluja)
class IdeaPlujaAdmin(admin.ModelAdmin):
    list_display = ('titol', 'font', 'proposta_associada', 'creat_per', 'creat_el')
    list_filter = ('font',)
    search_fields = ('titol', 'descripcio')


@admin.register(IdeaPublica)
class IdeaPublicaAdmin(admin.ModelAdmin):
    list_display = ('nom', 'email', 'processada', 'creat_el')
    list_filter = ('processada',)
    search_fields = ('nom', 'email', 'idea')
