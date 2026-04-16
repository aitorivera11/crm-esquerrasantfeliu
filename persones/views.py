from django.contrib import messages
from django.db.models import Q
from django.urls import reverse_lazy
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from agenda.models import Acte
from reunions.models import Reunio, Tasca
from core.mixins import RoleRequiredMixin
from usuaris.models import Usuari

from .forms import PersonaForm
from .models import Persona


class PersonesPermissionMixin(RoleRequiredMixin):
    allowed_roles = (Usuari.Rol.ADMINISTRACIO, Usuari.Rol.COORDINACIO)


class PersonaListView(PersonesPermissionMixin, ListView):
    model = Persona
    template_name = 'persones/persona_list.html'
    context_object_name = 'persones'

    def get_queryset(self):
        queryset = Persona.objects.prefetch_related('entitats').order_by('nom')
        q = self.request.GET.get('q', '').strip()
        if q:
            queryset = queryset.filter(
                Q(nom__icontains=q) | Q(email__icontains=q) | Q(telefon__icontains=q) | Q(entitats__nom__icontains=q)
            ).distinct()
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['q'] = self.request.GET.get('q', '').strip()
        return context


class PersonaCreateView(PersonesPermissionMixin, CreateView):
    model = Persona
    form_class = PersonaForm
    template_name = 'persones/persona_form.html'
    success_url = reverse_lazy('persones:persona_list')

    def form_valid(self, form):
        messages.success(self.request, 'Persona creada correctament.')
        return super().form_valid(form)


class PersonaUpdateView(PersonesPermissionMixin, UpdateView):
    model = Persona
    form_class = PersonaForm
    template_name = 'persones/persona_form.html'
    success_url = reverse_lazy('persones:persona_list')

    def form_valid(self, form):
        messages.success(self.request, 'Persona actualitzada correctament.')
        return super().form_valid(form)


class PersonaDetailView(PersonesPermissionMixin, DetailView):
    model = Persona
    template_name = 'persones/persona_detail.html'
    context_object_name = 'persona'

    def get_queryset(self):
        return Persona.objects.prefetch_related('entitats')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        persona = self.object
        context['reunions_relacionades'] = (
            Reunio.objects.filter(persones_relacionades=persona)
            .select_related('tipus', 'area')
            .distinct()
            .order_by('-inici')[:20]
        )
        context['tasques_relacionades'] = (
            Tasca.objects.filter(persones_relacionades=persona)
            .select_related('responsable', 'area', 'reunio_origen')
            .distinct()
            .order_by('-creat_el')[:20]
        )
        context['actes_relacionats'] = (
            Acte.objects.filter(persones_relacionades=persona)
            .select_related('tipus')
            .distinct()
            .order_by('-inici')[:20]
        )
        return context
