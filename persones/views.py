from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView, UpdateView

from .forms import PersonaForm
from .models import Persona


class PersonaListView(LoginRequiredMixin, ListView):
    model = Persona
    template_name = 'persones/persona_list.html'
    context_object_name = 'persones'

    def get_queryset(self):
        queryset = Persona.objects.order_by('nom')
        q = self.request.GET.get('q', '').strip()
        if q:
            queryset = queryset.filter(
                Q(nom__icontains=q) | Q(email__icontains=q) | Q(telefon__icontains=q)
            )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['q'] = self.request.GET.get('q', '').strip()
        return context


class PersonaCreateView(LoginRequiredMixin, CreateView):
    model = Persona
    form_class = PersonaForm
    template_name = 'persones/persona_form.html'
    success_url = reverse_lazy('persones:persona_list')

    def form_valid(self, form):
        messages.success(self.request, 'Persona creada correctament.')
        return super().form_valid(form)


class PersonaUpdateView(LoginRequiredMixin, UpdateView):
    model = Persona
    form_class = PersonaForm
    template_name = 'persones/persona_form.html'
    success_url = reverse_lazy('persones:persona_list')

    def form_valid(self, form):
        messages.success(self.request, 'Persona actualitzada correctament.')
        return super().form_valid(form)
