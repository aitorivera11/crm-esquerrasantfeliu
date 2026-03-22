import io
import os

from django.contrib import messages
from django.core.management import call_command
from django.db.models import Q
from django.http import JsonResponse
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, ListView, UpdateView

from core.mixins import RoleRequiredMixin
from core.models import Auditoria
from usuaris.models import Usuari

from .forms import EntitatForm
from .models import Entitat


class EntitatsPermissionMixin(RoleRequiredMixin):
    allowed_roles = (Usuari.Rol.ADMINISTRACIO, Usuari.Rol.COORDINACIO)


class EntitatListView(EntitatsPermissionMixin, ListView):
    model = Entitat
    template_name = 'entitats/entitat_list.html'
    context_object_name = 'entitats'

    def get_queryset(self):
        queryset = Entitat.objects.prefetch_related('persones').order_by('nom')
        q = self.request.GET.get('q', '').strip()
        if q:
            queryset = queryset.filter(
                Q(nom__icontains=q)
                | Q(email__icontains=q)
                | Q(telefon__icontains=q)
                | Q(web__icontains=q)
                | Q(tipologia__icontains=q)
                | Q(ambit__icontains=q)
                | Q(persones__nom__icontains=q)
            ).distinct()
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['q'] = self.request.GET.get('q', '').strip()
        return context


class EntitatCreateView(EntitatsPermissionMixin, CreateView):
    model = Entitat
    form_class = EntitatForm
    template_name = 'entitats/entitat_form.html'
    success_url = reverse_lazy('entitats:entitat_list')

    def form_valid(self, form):
        response = super().form_valid(form)
        Auditoria.objects.create(
            usuari=self.request.user,
            accio=Auditoria.Accio.CREATE,
            model_afectat='entitats.Entitat',
            object_id=str(self.object.pk),
            dades={'nom': self.object.nom},
        )
        messages.success(self.request, 'Entitat creada correctament.')
        return response


class EntitatUpdateView(EntitatsPermissionMixin, UpdateView):
    model = Entitat
    form_class = EntitatForm
    template_name = 'entitats/entitat_form.html'
    success_url = reverse_lazy('entitats:entitat_list')

    def form_valid(self, form):
        response = super().form_valid(form)
        Auditoria.objects.create(
            usuari=self.request.user,
            accio=Auditoria.Accio.UPDATE,
            model_afectat='entitats.Entitat',
            object_id=str(self.object.pk),
            dades={'nom': self.object.nom},
        )
        messages.success(self.request, 'Entitat actualitzada correctament.')
        return response


class ImportEntitiesCronView(View):
    http_method_names = ['get']

    def get(self, request):
        secret = os.getenv('CRON_SECRET', '')
        provided = request.headers.get('Authorization', '').removeprefix('Bearer ').strip() or request.GET.get('key', '')
        if secret and provided != secret:
            return JsonResponse({'ok': False, 'error': 'Unauthorized'}, status=401)

        output = io.StringIO()
        call_command('import_entities', '--cleanup', stdout=output)
        return JsonResponse({'ok': True, 'details': output.getvalue().strip()})
