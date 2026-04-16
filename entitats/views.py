import io
import json
import os

from django.contrib import messages
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db.models import Q
from django.http import JsonResponse
from django.urls import reverse_lazy
from django.shortcuts import redirect
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from agenda.models import Acte
from core.mixins import RoleRequiredMixin
from core.models import Auditoria
from reunions.models import Reunio, Tasca
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


class EntitatDetailView(EntitatsPermissionMixin, DetailView):
    model = Entitat
    template_name = 'entitats/entitat_detail.html'
    context_object_name = 'entitat'

    def get_queryset(self):
        return Entitat.objects.prefetch_related('persones')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        entitat = self.object
        context['reunions_relacionades'] = (
            Reunio.objects.filter(entitats_relacionades=entitat)
            .select_related('tipus', 'area')
            .distinct()
            .order_by('-inici')[:20]
        )
        context['tasques_relacionades'] = (
            Tasca.objects.filter(entitats_relacionades=entitat)
            .select_related('responsable', 'area', 'reunio_origen')
            .distinct()
            .order_by('-creat_el')[:20]
        )
        context['actes_relacionats'] = (
            Acte.objects.filter(entitats_relacionades=entitat)
            .select_related('tipus')
            .distinct()
            .order_by('-inici')[:20]
        )
        return context


class ImportEntitiesCronView(View):
    http_method_names = ['get']

    def get(self, request):
        secret = os.getenv('CRON_SECRET', '')
        provided = request.headers.get('Authorization', '').removeprefix('Bearer ').strip() or request.GET.get('key', '')
        if secret and provided != secret:
            return JsonResponse({'ok': False, 'error': 'Unauthorized'}, status=401)

        return self._run_import()

    def _run_import(self):
        output = io.StringIO()
        try:
            call_command('import_entities', '--cleanup', stdout=output)
        except CommandError as exc:
            return JsonResponse({'ok': False, 'error': str(exc), 'details': output.getvalue().strip()}, status=500)
        return JsonResponse({'ok': True, 'details': output.getvalue().strip()})


class SyncImportedEntitiesView(EntitatsPermissionMixin, View):
    http_method_names = ['post']

    def post(self, request):
        output = io.StringIO()
        try:
            call_command('import_entities', '--cleanup', stdout=output)
        except CommandError as exc:
            messages.error(request, f'La sincronització d’entitats ha fallat: {exc}')
            return self._redirect()

        stats = self._extract_stats(output.getvalue())
        if stats:
            messages.success(
                request,
                (
                    "Sincronització d’entitats completada. "
                    f"Importades: {stats.get('created', 0)} noves, "
                    f"{stats.get('updated', 0)} actualitzades, "
                    f"{stats.get('removed', 0)} eliminades."
                ),
            )
        else:
            messages.success(request, 'Sincronització d’entitats completada.')
        return self._redirect()

    def _extract_stats(self, raw_output):
        for line in reversed([item.strip() for item in raw_output.splitlines() if item.strip()]):
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                continue
        return None

    def _redirect(self):
        return redirect('entitats:entitat_list')
