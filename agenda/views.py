import logging
from datetime import datetime, timedelta
import io
import json
import os
from pathlib import Path
from urllib.parse import quote
from uuid import uuid4

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.core.management import call_command
from django.core.management.base import CommandError
from django.core.files import File
from django.core.files.storage import default_storage
from django.db.models import Count, Prefetch, Q
from django.http import Http404, HttpResponse, HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import CreateView, DetailView, ListView, UpdateView
from django.urls import reverse

from core.models import Auditoria

from .forms import ActeForm, InstagramImportForm, ParticipacioForm
from .models import Acte, ActeTipus, ParticipacioActe, SegmentVisibilitat
from .services import parse_instagram_event_data

logger = logging.getLogger(__name__)


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


    def _base_queryset(self):
        current_user_participation = Prefetch(
            'participants',
            queryset=ParticipacioActe.objects.filter(usuari=self.request.user).select_related('usuari'),
            to_attr='participant_for_request_user',
        )
        return (
            Acte.objects.select_related('creador', 'tipus', 'reunio_relacionada')
            .prefetch_related(
                'participants__usuari',
                'visible_per',
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
        acte.persones_relacionades_list = list(acte.persones_relacionades.all())
        acte.entitats_relacionades_list = list(acte.entitats_relacionades.all())
        acte.user_can_manage = self._user_can_manage_actes()
        acte.user_can_attend = acte.estat == Acte.Estat.PUBLICAT or acte.user_can_manage
        acte.user_can_view_admin_details = self._user_can_view_admin_details()
        acte.reunio_relacionada_obj = getattr(acte, 'reunio_relacionada', None)
        color = (acte.tipus.color or '').strip() if acte.tipus_id else ''
        acte.tipus_color = color or '#6c7a89'
        acte.tipus_style = f'--type-accent: {acte.tipus_color};' if acte.tipus_id else ''
        return acte


class ActeListView(AgendaContextMixin, LoginRequiredMixin, ListView):
    model = Acte
    template_name = 'agenda/acte_list.html'
    context_object_name = 'actes'

    def _is_true(self, value):
        return str(value).lower() in {'1', 'true', 'on', 'si', 'yes'}

    def _parse_date(self, value):
        if not value:
            return None
        try:
            return timezone.datetime.fromisoformat(value).date()
        except ValueError:
            return None

    def _format_calendar_datetime(self, value):
        return EventSharingMixin._format_calendar_datetime(self, value)

    def _sharing_context(self, acte):
        return EventSharingMixin._sharing_context(self, acte)

    def get_queryset(self):
        user_can_edit = self._user_can_manage_actes()
        queryset = self._visible_queryset(include_drafts=user_can_edit)
        now = timezone.now()
        today = timezone.localdate()
        default_end = today + timedelta(days=6)
        show_past = self._is_true(self.request.GET.get('show_past'))
        show_imported = self._is_true(self.request.GET.get('show_imported'))

        day = self._parse_date(self.request.GET.get('day'))
        date_from = self._parse_date(self.request.GET.get('date_from'))
        date_to = self._parse_date(self.request.GET.get('date_to'))

        if day:
            date_from = day
            date_to = day
        elif not (date_from or date_to):
            date_from = today
            date_to = default_end

        if date_from and date_to and date_from > date_to:
            date_from, date_to = date_to, date_from

        if date_from:
            queryset = queryset.filter(inici__date__gte=date_from)
        elif not show_past:
            queryset = queryset.filter(inici__gte=now)

        if date_to:
            queryset = queryset.filter(inici__date__lte=date_to)

        if not show_past and not date_from and not day:
            queryset = queryset.filter(inici__gte=now)

        if not show_imported:
            queryset = queryset.filter(external_source='')

        search = (self.request.GET.get('q') or '').strip()
        if search:
            queryset = queryset.filter(
                Q(titol__icontains=search)
                | Q(descripcio__icontains=search)
                | Q(ubicacio__icontains=search)
                | Q(punt_trobada__icontains=search)
            )

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

        return queryset.order_by('-es_important', 'inici').distinct()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        actes = []
        for acte in context['actes']:
            acte = self._enrich_acte(acte)
            if self._user_can_manage_actes():
                for key, value in self._sharing_context(acte).items():
                    setattr(acte, key, value)
            actes.append(acte)
        now = timezone.now()
        visible_base = self._visible_queryset(include_drafts=self._user_can_manage_actes())
        today = timezone.localdate()
        default_end = today + timedelta(days=6)
        current_filters = {
            'q': self.request.GET.get('q', ''),
            'day': self.request.GET.get('day', ''),
            'date_from': self.request.GET.get('date_from', today.isoformat()),
            'date_to': self.request.GET.get('date_to', default_end.isoformat()),
            'my_status': self.request.GET.get('my_status', ''),
            'tipus': self.request.GET.get('tipus', ''),
            'estat': self.request.GET.get('estat', ''),
            'visibility': self.request.GET.get('visibility', ''),
            'show_past': self._is_true(self.request.GET.get('show_past')),
            'show_imported': self._is_true(self.request.GET.get('show_imported')),
        }
        if current_filters['day']:
            current_filters['date_from'] = current_filters['day']
            current_filters['date_to'] = current_filters['day']
        has_active_filters = any(
            [
                current_filters['q'],
                current_filters['day'],
                current_filters['my_status'],
                current_filters['tipus'],
                current_filters['estat'],
                current_filters['visibility'],
                current_filters['show_past'],
                current_filters['show_imported'],
                current_filters['date_from'] != today.isoformat(),
                current_filters['date_to'] != default_end.isoformat(),
            ]
        )
        context.update(
            {
                'actes': actes,
                'imported_count': visible_base.filter(external_source='AGENDA_CIUTAT', estat=Acte.Estat.PUBLICAT).count(),
                'upcoming_count': visible_base.filter(inici__gte=now, estat=Acte.Estat.PUBLICAT).count(),
                'past_count': visible_base.filter(inici__lt=now).count(),
                'draft_count': visible_base.filter(estat=Acte.Estat.ESBORRANY).count(),
                'tipus_options': ActeTipus.objects.filter(actiu=True),
                'current_filters': current_filters,
                'filters_open': has_active_filters,
                'important_count': visible_base.filter(es_important=True, estat=Acte.Estat.PUBLICAT).count(),
                'can_manage_actes': self._user_can_manage_actes(),
                'can_view_admin_details': self._user_can_view_admin_details(),
            }
        )
        return context



class EventSharingMixin:
    def _format_calendar_datetime(self, value):
        local_value = timezone.localtime(value)
        return local_value.strftime('%Y%m%dT%H%M%S')

    def _build_ics_content(self, acte):
        start = self._format_calendar_datetime(acte.inici)
        end_value = acte.fi or (acte.inici + timedelta(hours=1))
        end = self._format_calendar_datetime(end_value)
        absolute_url = self.request.build_absolute_uri(acte.get_absolute_url())
        location = (acte.ubicacio or '').replace('\n', ' ').strip()
        description_lines = [acte.descripcio.strip()] if acte.descripcio else []
        if location:
            description_lines.append(f'Lloc: {location}')
        description_lines.append(f'Més informació: {absolute_url}')
        description = '\n'.join(line for line in description_lines if line).replace('\r', '')

        def escape(value):
            return (
                str(value or '')
                .replace('\\', '\\\\')
                .replace(';', r'\;')
                .replace(',', r'\,')
                .replace('\n', r'\n')
            )

        return '\r\n'.join([
            'BEGIN:VCALENDAR',
            'VERSION:2.0',
            'PRODID:-//CRM Campanya Sant Feliu//Agenda//CA',
            'CALSCALE:GREGORIAN',
            'BEGIN:VEVENT',
            f'UID:acte-{acte.pk}@crm-esquerrasantfeliu',
            f'DTSTAMP:{timezone.now().strftime("%Y%m%dT%H%M%SZ")}',
            f'DTSTART:{start}',
            f'DTEND:{end}',
            f'SUMMARY:{escape(acte.titol)}',
            f'DESCRIPTION:{escape(description)}',
            f'LOCATION:{escape(location)}',
            f'URL:{escape(absolute_url)}',
            'END:VEVENT',
            'END:VCALENDAR',
            '',
        ])

    def _sharing_context(self, acte):
        absolute_url = self.request.build_absolute_uri(acte.get_absolute_url())
        share_lines = [
            acte.titol,
            f"📅 {timezone.localtime(acte.inici).strftime('%d/%m/%Y %H:%M')} h",
        ]
        if acte.fi:
            share_lines.append(f"⏱️ Fins a les {timezone.localtime(acte.fi).strftime('%H:%M')} h")
        if acte.ubicacio:
            share_lines.append(f"📍 {acte.ubicacio}")
        share_lines.extend(['', absolute_url])
        share_text = '\n'.join(share_lines)

        details = [acte.descripcio.strip()] if acte.descripcio else []
        if acte.ubicacio:
            details.append(f'Lloc: {acte.ubicacio}')
        details.append(f'Enllaç: {absolute_url}')
        share_body = '\n\n'.join([part for part in details if part])

        google_dates = f"{self._format_calendar_datetime(acte.inici)}/{self._format_calendar_datetime(acte.fi or (acte.inici + timedelta(hours=1)))}"
        google_params = {
            'action': 'TEMPLATE',
            'text': acte.titol,
            'dates': google_dates,
            'details': share_body,
            'location': acte.ubicacio or '',
        }
        google_url = 'https://calendar.google.com/calendar/render?' + '&'.join(
            f'{key}={quote(str(value))}' for key, value in google_params.items() if value
        )

        return {
            'share_url': absolute_url,
            'share_text': share_text,
            'whatsapp_url': f'https://wa.me/?text={quote(share_text)}',
            'email_url': f'mailto:?subject={quote(acte.titol)}&body={quote(share_text)}',
            'google_calendar_url': google_url,
            'ics_url': self.request.build_absolute_uri(reverse('agenda:acte_ics', kwargs={'pk': acte.pk})),
        }


class ActeDetailView(EventSharingMixin, AgendaContextMixin, LoginRequiredMixin, DetailView):
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
        context.update(self._sharing_context(self.object))
        return context


class ActeIcsView(EventSharingMixin, AgendaContextMixin, LoginRequiredMixin, DetailView):
    model = Acte

    def get_queryset(self):
        return self._visible_queryset(include_drafts=self._user_can_manage_actes())

    def render_to_response(self, context, **response_kwargs):
        acte = self.get_object()
        filename = f"{acte.titol.lower().replace(' ', '-')[:60] or 'acte'}.ics"
        response = HttpResponse(self._build_ics_content(acte), content_type='text/calendar; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response


class ActeCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = Acte
    form_class = ActeForm
    template_name = 'agenda/acte_form.html'
    permission_required = 'agenda.add_acte'

    def _session_key(self):
        return 'agenda_instagram_prefill'

    def _attach_prefill_image_if_needed(self, form, prefill_data):
        if not prefill_data or form.cleaned_data.get('imatge'):
            return
        image_tmp_path = (prefill_data or {}).get('import_image_tmp_path') or ''
        if not image_tmp_path or not default_storage.exists(image_tmp_path):
            return

        with default_storage.open(image_tmp_path, 'rb') as file_handle:
            filename = Path(image_tmp_path).name.split('_', 1)[-1]
            form.instance.imatge.save(filename, File(file_handle), save=False)

    def _build_initial_from_instagram_prefill(self, prefill_data):
        fields = (prefill_data or {}).get('fields') or {}
        initial = {}

        if fields.get('title'):
            initial['titol'] = fields['title']
        if fields.get('description'):
            initial['descripcio'] = fields['description']
        if fields.get('location'):
            initial['ubicacio'] = fields['location']

        date_value = fields.get('date')
        start_time = fields.get('start_time') or '19:00'
        end_time = fields.get('end_time')
        if date_value:
            try:
                start_dt = datetime.fromisoformat(f'{date_value}T{start_time}')
                initial['inici'] = start_dt.strftime('%Y-%m-%dT%H:%M')
                if end_time:
                    end_dt = datetime.fromisoformat(f'{date_value}T{end_time}')
                    if end_dt > start_dt:
                        initial['fi'] = end_dt.strftime('%Y-%m-%dT%H:%M')
            except ValueError:
                pass

        return initial

    def get_initial(self):
        initial = super().get_initial()
        prefill_data = self.request.session.get(self._session_key())
        if prefill_data:
            initial.update(self._build_initial_from_instagram_prefill(prefill_data))
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        prefill_data = self.request.session.get(self._session_key())
        context['instagram_prefill'] = prefill_data
        return context

    def form_valid(self, form):
        form.instance.creador = self.request.user
        prefill_data = self.request.session.get(self._session_key())
        self._attach_prefill_image_if_needed(form, prefill_data)
        if prefill_data:
            fields = prefill_data.get('fields') or {}
            form.instance.source_url = fields.get('source_url', '')
            form.instance.external_source = 'INSTAGRAM'
            form.instance.source_payload = {
                'municipality': fields.get('municipality', ''),
                'organizer': fields.get('organizer', ''),
                'raw_text': prefill_data.get('raw_text', ''),
                'ocr_text': prefill_data.get('ocr_text', ''),
            }
        response = super().form_valid(form)
        if prefill_data:
            image_tmp_path = prefill_data.get('import_image_tmp_path')
            if image_tmp_path and default_storage.exists(image_tmp_path):
                default_storage.delete(image_tmp_path)
            self.request.session.pop(self._session_key(), None)
            self.request.session.modified = True
        Auditoria.objects.create(
            usuari=self.request.user,
            accio=Auditoria.Accio.CREATE,
            model_afectat='agenda.Acte',
            object_id=str(self.object.pk),
            dades={'titol': self.object.titol, 'estat': self.object.estat},
        )
        return response


class InstagramActeImportView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = 'agenda.add_acte'
    template_name = 'agenda/instagram_import_form.html'

    def _session_key(self):
        return 'agenda_instagram_prefill'

    def get(self, request):
        form = InstagramImportForm()
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = InstagramImportForm(request.POST, request.FILES)
        if not form.is_valid():
            return render(request, self.template_name, {'form': form})

        try:
            payload = parse_instagram_event_data(
                instagram_url=form.cleaned_data.get('instagram_url', ''),
                manual_text=form.cleaned_data.get('text_manual', ''),
                image_file=form.cleaned_data.get('imatge'),
                observations=form.cleaned_data.get('observacions', ''),
            )
        except Exception:
            logger.exception("Error important esdeveniment des d'Instagram.")
            form.add_error(None, "No s'ha pogut importar la publicació ara mateix. Revisa les dades i torna-ho a provar.")
            messages.error(request, "No s'ha pogut completar la importació d'Instagram.")
            return render(request, self.template_name, {'form': form})

        import_image_tmp_path = ''
        uploaded_image = form.cleaned_data.get('imatge')
        if uploaded_image:
            safe_name = uploaded_image.name.replace('/', '_')
            import_image_tmp_path = default_storage.save(
                f'agenda/tmp_imports/{uuid4().hex}_{safe_name}',
                uploaded_image,
            )

        request.session[self._session_key()] = {
            'fields': payload.get('fields', {}),
            'raw_text': payload.get('raw_text', ''),
            'ocr_text': payload.get('ocr_text', ''),
            'import_image_tmp_path': import_image_tmp_path,
            'warnings': payload.get('warnings', []),
        }
        request.session.modified = True

        for warning in payload.get('warnings', []):
            messages.warning(request, warning)
        messages.success(request, 'S’ha preparat un esborrany d’acte amb la informació detectada.')
        return redirect('agenda:acte_create')


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
            reunio = getattr(acte, 'reunio_relacionada', None)
            if reunio:
                if participacio.intencio == ParticipacioActe.Intencio.HI_ANIRE:
                    reunio.assistents.add(request.user)
                else:
                    reunio.assistents.remove(request.user)
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

    def _is_true(self, value):
        return str(value).lower() in {'1', 'true', 'on', 'si', 'yes'}

    def get_queryset(self):
        return (
            ParticipacioActe.objects.filter(
                usuari=self.request.user,
                intencio=ParticipacioActe.Intencio.HI_ANIRE,
                acte__inici__gte=timezone.now(),
            )
            .select_related('acte', 'acte__tipus')
            .order_by('acte__inici')
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        show_attended = self._is_true(self.request.GET.get('show_attended'))
        attended_queryset = (
            ParticipacioActe.objects.filter(
                usuari=self.request.user,
                acte__inici__lt=timezone.now(),
                assistencia_real=ParticipacioActe.AssistenciaReal.ASSISTEIX,
            )
            .select_related('acte', 'acte__tipus')
            .order_by('-acte__inici')
        )
        context.update(
            {
                'show_attended': show_attended,
                'attended_count': attended_queryset.count(),
                'attended_participacions': attended_queryset if show_attended else [],
            }
        )
        return context


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


class SyncImportedEventsView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = 'agenda.change_acte'
    raise_exception = True
    http_method_names = ['post']

    def post(self, request):
        output = io.StringIO()
        try:
            call_command('import_city_events', '--cleanup', stdout=output)
        except CommandError as exc:
            messages.error(request, f"La sincronització d'actes importats ha fallat: {exc}")
            return redirect('agenda:acte_list')
        stats = self._extract_stats(output.getvalue())
        if stats:
            messages.success(
                request,
                (
                    "Sincronització completada. "
                    f"Importats: {stats.get('created', 0)} nous, "
                    f"{stats.get('updated', 0)} actualitzats, "
                    f"{stats.get('cleanup', 0)} eliminats."
                ),
            )
        else:
            messages.success(request, "Sincronització completada. Els actes importats s'han actualitzat com a publicats.")
        return redirect('agenda:acte_list')

    def _extract_stats(self, raw_output):
        for line in reversed([item.strip() for item in raw_output.splitlines() if item.strip()]):
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                continue
        return None


@method_decorator(csrf_exempt, name="dispatch")
class ImportCityEventsCronView(View):
    http_method_names = ['get']

    def get(self, request):
        secret = os.getenv('CRON_SECRET', '')
        provided = request.headers.get('Authorization', '').removeprefix('Bearer ').strip() or request.GET.get('key', '')
        if secret and provided != secret:
            return JsonResponse({'ok': False, 'error': 'Unauthorized'}, status=401)

        output = io.StringIO()
        try:
            call_command('import_city_events', '--cleanup', stdout=output)
        except CommandError as exc:
            return JsonResponse({'ok': False, 'error': str(exc), 'details': output.getvalue().strip()}, status=500)
        return JsonResponse({'ok': True, 'details': output.getvalue().strip()})
