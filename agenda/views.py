import io
import os

from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.core.management import call_command
from django.db.models import Count, Prefetch, Q
from django.http import Http404, HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from core.models import Auditoria

from .forms import ActeForm, ParticipacioForm
from .models import Acte, ActeTipus, ParticipacioActe, SegmentVisibilitat


class AgendaContextMixin:
    def _user_segments_filter(self):
        user = self.request.user
        filters = Q(ambit=SegmentVisibilitat.Ambit.ROL, codi=user.rol)
        if user.tipus:
            filters |= Q(ambit=SegmentVisibilitat.Ambit.TIPUS, codi=user.tipus)
        return filters

    def _visibility_filter(self):
        return Q(visible_per__isnull=True) | Q(visible_per__in=SegmentVisibilitat.objects.filter(self._user_segments_filter()))

    def _user_can_manage_actes(self):
        return self.request.user.has_perm('agenda.change_acte')

    def _user_can_view_admin_details(self):
        return self.request.user.has_perm('agenda.can_view_participants')

    def _allowed_attendance(self, acte):
        attendance_segments = list(acte.assistencia_permesa_per.all())
        if not attendance_segments:
            return True
        return any(
            (segment.ambit == SegmentVisibilitat.Ambit.ROL and segment.codi == self.request.user.rol)
            or (segment.ambit == SegmentVisibilitat.Ambit.TIPUS and segment.codi == self.request.user.tipus)
            for segment in attendance_segments
        )

    def _base_queryset(self):
        current_user_participation = Prefetch(
            'participants',
            queryset=ParticipacioActe.objects.filter(usuari=self.request.user).select_related('usuari'),
            to_attr='participant_for_request_user',
        )
        return (
            Acte.objects.select_related('creador', 'tipus')
            .prefetch_related(
                'participants__usuari',
                'visible_per',
                'assistencia_permesa_per',
                'persones_relacionades__entitats',
                'entitats_relacionades__persones',
                current_user_participation,
            )
            .annotate(
                total_participants=Count('participants', distinct=True),
                total_confirmats=Count('participants', filter=Q(participants__intencio=ParticipacioActe.Intencio.HI_ANIRE), distinct=True),
                total_potser=Count('participants', filter=Q(participants__intencio=ParticipacioActe.Intencio.POTSER), distinct=True),
                total_no=Count('participants', filter=Q(participants__intencio=ParticipacioActe.Intencio.NO_HI_ANIRE), distinct=True),
            )
            .distinct()
        )

    def _visible_queryset(self, include_drafts=False):
        queryset = self._base_queryset()
        if self._user_can_manage_actes():
            if not include_drafts:
                queryset = queryset.filter(estat=Acte.Estat.PUBLICAT)
            return queryset.distinct()
        queryset = queryset.filter(estat=Acte.Estat.PUBLICAT)
        return queryset.filter(self._visibility_filter()).distinct()

    def _enrich_acte(self, acte):
        participants = list(acte.participants.all())
        confirmats = [p for p in participants if p.intencio == ParticipacioActe.Intencio.HI_ANIRE]
        acte.confirmats_preview = confirmats[:4]
        acte.confirmats_extra = max(len(confirmats) - len(acte.confirmats_preview), 0)
        acte.request_user_participacio = next(iter(getattr(acte, 'participant_for_request_user', [])), None)
        acte.visible_segments_labels = [segment.etiqueta for segment in acte.visible_per.all()]
        acte.assistencia_segments_labels = [segment.etiqueta for segment in acte.assistencia_permesa_per.all()]
        acte.persones_relacionades_list = list(acte.persones_relacionades.all())
        acte.entitats_relacionades_list = list(acte.entitats_relacionades.all())
        acte.user_can_attend = self._allowed_attendance(acte)
        acte.user_can_manage = self._user_can_manage_actes()
        acte.user_can_view_admin_details = self._user_can_view_admin_details()
        return acte


class ActeListView(AgendaContextMixin, LoginRequiredMixin, ListView):
    model = Acte
    template_name = 'agenda/acte_list.html'
    context_object_name = 'actes'

    def _is_true(self, value):
        return str(value).lower() in {'1', 'true', 'on', 'si', 'yes'}

    def get_queryset(self):
        user_can_edit = self._user_can_manage_actes()
        queryset = self._visible_queryset(include_drafts=user_can_edit)
        now = timezone.now()
        show_past = self._is_true(self.request.GET.get('show_past'))

        day = self.request.GET.get('day')
        if not show_past and not day:
            queryset = queryset.filter(inici__gte=now)

        if day:
            queryset = queryset.filter(inici__date=day)

        estat = self.request.GET.get('estat')
        if estat in Acte.Estat.values:
            queryset = queryset.filter(estat=estat)

        tipus = self.request.GET.get('tipus')
        if tipus:
            queryset = queryset.filter(tipus_id=tipus)

        visibility = self.request.GET.get('visibility')
        if visibility == 'restricted':
            queryset = queryset.filter(visible_per__isnull=False)
        elif visibility == 'open':
            queryset = queryset.filter(visible_per__isnull=True)

        my_status = self.request.GET.get('my_status')
        if my_status == 'confirmed':
            queryset = queryset.filter(participants__usuari=self.request.user, participants__intencio=ParticipacioActe.Intencio.HI_ANIRE)
        elif my_status == 'pending':
            queryset = queryset.exclude(participants__usuari=self.request.user)
        elif my_status in ParticipacioActe.Intencio.values:
            queryset = queryset.filter(participants__usuari=self.request.user, participants__intencio=my_status)

        return queryset.order_by('inici').distinct()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        actes = [self._enrich_acte(acte) for acte in context['actes']]
        now = timezone.now()
        visible_base = self._visible_queryset(include_drafts=self._user_can_manage_actes())
        current_filters = {
            'day': self.request.GET.get('day', ''),
            'my_status': self.request.GET.get('my_status', ''),
            'tipus': self.request.GET.get('tipus', ''),
            'estat': self.request.GET.get('estat', ''),
            'visibility': self.request.GET.get('visibility', ''),
            'show_past': self._is_true(self.request.GET.get('show_past')),
        }
        context.update(
            {
                'actes': actes,
                'imported_count': visible_base.filter(external_source='AGENDA_CIUTAT', estat=Acte.Estat.PUBLICAT).count(),
                'upcoming_count': visible_base.filter(inici__gte=now, estat=Acte.Estat.PUBLICAT).count(),
                'past_count': visible_base.filter(inici__lt=now).count(),
                'draft_count': visible_base.filter(estat=Acte.Estat.ESBORRANY).count(),
                'tipus_options': ActeTipus.objects.filter(actiu=True),
                'current_filters': current_filters,
                'filters_open': any(current_filters.values()),
                'can_manage_actes': self._user_can_manage_actes(),
                'can_view_admin_details': self._user_can_view_admin_details(),
            }
        )
        return context


class ActeDetailView(AgendaContextMixin, LoginRequiredMixin, DetailView):
    model = Acte
    template_name = 'agenda/acte_detail.html'
    context_object_name = 'acte'

    def get_queryset(self):
        queryset = self._visible_queryset(include_drafts=self._user_can_manage_actes())
        return queryset

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        if obj.estat != Acte.Estat.PUBLICAT and not self._user_can_manage_actes():
            raise Http404
        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        self.object = self._enrich_acte(self.object)
        participacio = self.object.request_user_participacio
        context['participacio'] = participacio
        context['participacio_form'] = ParticipacioForm(instance=participacio, usuari=self.request.user, acte=self.object)
        context['can_manage_actes'] = self._user_can_manage_actes()
        context['can_view_admin_details'] = self._user_can_view_admin_details()
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


class ParticiparActeView(AgendaContextMixin, LoginRequiredMixin, View):
    http_method_names = ['post']

    def post(self, request, pk):
        acte = get_object_or_404(self._visible_queryset(include_drafts=self._user_can_manage_actes()), pk=pk)
        acte = self._enrich_acte(acte)
        if not acte.user_can_attend:
            return HttpResponseForbidden("No tens permís per confirmar assistència en aquest acte.")

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
            acte = self._enrich_acte(self._base_queryset().get(pk=acte.pk))
            render_mode = request.POST.get('render_mode', 'detail')
            context = {
                'acte': acte,
                'participacio': participacio,
                'participacio_form': ParticipacioForm(instance=participacio, usuari=request.user, acte=acte),
            }
            if render_mode == 'card':
                return render(request, 'agenda/components/acte_card.html', context)
            return render(request, 'agenda/components/participacio_buttons.html', context)

        if request.headers.get('HX-Request'):
            return render(request, 'agenda/components/participacio_form.html', {'form': form, 'acte': acte}, status=400)
        return HttpResponseForbidden('Participació no vàlida.')


class ParticipantsListView(AgendaContextMixin, LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = Acte
    template_name = 'agenda/participants_list.html'
    context_object_name = 'acte'
    permission_required = 'agenda.can_view_participants'

    def get_queryset(self):
        return self._base_queryset()


class ElsMeusActesView(LoginRequiredMixin, ListView):
    model = ParticipacioActe
    template_name = 'agenda/els_meus_actes.html'
    context_object_name = 'participacions'

    def get_queryset(self):
        return (
            ParticipacioActe.objects.filter(usuari=self.request.user)
            .select_related('acte', 'acte__tipus')
            .order_by('-acte__inici')
        )


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
