import io
import os

from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.core.management import call_command
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from core.models import Auditoria

from .forms import ActeForm, ParticipacioForm
from .models import Acte, ParticipacioActe


class ActeListView(LoginRequiredMixin, ListView):
    model = Acte
    template_name = 'agenda/acte_list.html'
    context_object_name = 'actes'

    def get_queryset(self):
        queryset = Acte.objects.select_related('creador').prefetch_related('participants__usuari')
        if self.request.user.has_perm('agenda.change_acte'):
            return queryset
        return queryset.filter(estat=Acte.Estat.PUBLICAT)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['imported_count'] = Acte.objects.filter(external_source='AGENDA_CIUTAT', estat=Acte.Estat.PUBLICAT).count()
        return context


class ActeDetailView(LoginRequiredMixin, DetailView):
    model = Acte
    template_name = 'agenda/acte_detail.html'
    context_object_name = 'acte'

    def get_queryset(self):
        queryset = Acte.objects.select_related('creador').prefetch_related('participants__usuari')
        if self.request.user.has_perm('agenda.change_acte'):
            return queryset
        return queryset.filter(estat=Acte.Estat.PUBLICAT)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        participacio = ParticipacioActe.objects.filter(acte=self.object, usuari=self.request.user).first()
        context['participacio'] = participacio
        context['participacio_form'] = ParticipacioForm(instance=participacio, usuari=self.request.user, acte=self.object)
        return context


class ActeCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = Acte
    form_class = ActeForm
    template_name = 'agenda/acte_form.html'
    permission_required = 'agenda.add_acte'

    def form_valid(self, form):
        form.instance.creador = self.request.user
        response = super().form_valid(form)
        Auditoria.objects.create(
            usuari=self.request.user,
            accio=Auditoria.Accio.CREATE,
            model_afectat='agenda.Acte',
            object_id=str(self.object.pk),
            dades={'titol': self.object.titol, 'estat': self.object.estat},
        )
        return response


class ActeUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = Acte
    form_class = ActeForm
    template_name = 'agenda/acte_form.html'
    permission_required = 'agenda.change_acte'

    def form_valid(self, form):
        response = super().form_valid(form)
        Auditoria.objects.create(
            usuari=self.request.user,
            accio=Auditoria.Accio.UPDATE,
            model_afectat='agenda.Acte',
            object_id=str(self.object.pk),
            dades={'titol': self.object.titol, 'estat': self.object.estat},
        )
        return response


class ParticiparActeView(LoginRequiredMixin, View):
    http_method_names = ['post']

    def post(self, request, pk):
        acte = get_object_or_404(Acte, pk=pk)
        participacio = ParticipacioActe.objects.filter(acte=acte, usuari=request.user).first()
        form = ParticipacioForm(request.POST, instance=participacio, usuari=request.user, acte=acte)
        if form.is_valid():
            participacio = form.save(commit=False)
            participacio.usuari = request.user
            participacio.acte = acte
            participacio.save()
            Auditoria.objects.create(
                usuari=request.user,
                accio=Auditoria.Accio.STATUS,
                model_afectat='agenda.ParticipacioActe',
                object_id=str(participacio.pk),
                dades={
                    'acte_id': acte.pk,
                    'intencio': participacio.intencio,
                    'assistencia_real': participacio.assistencia_real,
                },
            )
            template = 'agenda/components/participacio_buttons.html'
            context = {'acte': acte, 'participacio': participacio, 'participacio_form': ParticipacioForm(instance=participacio, usuari=request.user, acte=acte)}
            return render(request, template, context)

        if request.headers.get('HX-Request'):
            return render(request, 'agenda/components/participacio_form.html', {'form': form, 'acte': acte}, status=400)
        return HttpResponseForbidden('Participació no vàlida.')


class ParticipantsListView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = Acte
    template_name = 'agenda/participants_list.html'
    context_object_name = 'acte'
    permission_required = 'agenda.can_view_participants'


class ElsMeusActesView(LoginRequiredMixin, ListView):
    model = ParticipacioActe
    template_name = 'agenda/els_meus_actes.html'
    context_object_name = 'participacions'

    def get_queryset(self):
        return ParticipacioActe.objects.filter(usuari=self.request.user).select_related('acte')


class MarcarAssistenciaView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = 'agenda.can_mark_attendance'
    http_method_names = ['post']

    def post(self, request, pk, participant_pk):
        acte = get_object_or_404(Acte, pk=pk)
        participacio = get_object_or_404(ParticipacioActe, pk=participant_pk, acte=acte)
        estat = request.POST.get('assistencia_real')
        if estat not in ParticipacioActe.AssistenciaReal.values:
            return HttpResponseForbidden("Estat d'assistència no vàlid.")
        participacio.assistencia_real = estat
        participacio.save(update_fields=['assistencia_real', 'actualitzat_el'])
        Auditoria.objects.create(
            usuari=request.user,
            accio=Auditoria.Accio.STATUS,
            model_afectat='agenda.ParticipacioActe',
            object_id=str(participacio.pk),
            dades={'assistencia_real': estat, 'acte_id': acte.pk},
        )
        return redirect('agenda:participants_list', pk=pk)


@method_decorator(csrf_exempt, name="dispatch")
class ImportCityEventsCronView(View):
    http_method_names = ['get']

    def get(self, request):
        secret = os.getenv('CRON_SECRET', '')
        provided = request.headers.get('Authorization', '').removeprefix('Bearer ').strip() or request.GET.get('key', '')
        if secret and provided != secret:
            return JsonResponse({'ok': False, 'error': 'Unauthorized'}, status=401)

        output = io.StringIO()
        call_command('import_city_events', '--cleanup', stdout=output)
        return JsonResponse({'ok': True, 'details': output.getvalue().strip()})
