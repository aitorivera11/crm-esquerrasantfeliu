from datetime import datetime
import re
from urllib.parse import quote

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db import transaction
from django.db.models import Count, Max, Prefetch, Q
from django.http import HttpResponse, HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.views.generic import CreateView, DetailView, ListView, TemplateView, UpdateView

from core.mixins import RoleRequiredMixin
from usuaris.models import Usuari

from .forms import (
    ActaForm,
    PuntActaForm,
    PuntOrdreDiaForm,
    ReunioForm,
    SeguimentTascaForm,
    TascaForm,
    TascaRapidaReunioForm,
    TascaRelacioReunioForm,
    inicialitzar_punts_acta_des_de_ordre_dia,
    sincronitzar_punts_acta_amb_ordre_dia,
)
from .models import Acta, PuntActa, PuntOrdreDia, Reunio, SeguimentTasca, Tasca, TascaRelacioReunio


class ReunionsPermissionMixin(RoleRequiredMixin):
    allowed_roles = (Usuari.Rol.ADMINISTRACIO, Usuari.Rol.COORDINACIO)


class ReunionsBaseMixin(ReunionsPermissionMixin):
    def get_success_url(self):
        return self.object.get_absolute_url()


class ReunionsWritePermissionMixin(PermissionRequiredMixin):
    raise_exception = True


class ReunioWritePermissionMixin(ReunionsWritePermissionMixin):
    permission_required = 'reunions.change_reunio'


class TascaWritePermissionMixin(ReunionsWritePermissionMixin):
    permission_required = 'reunions.change_tasca'

def tasques_obertes_queryset(queryset=None):
    base_queryset = queryset if queryset is not None else Tasca.objects.all()
    return base_queryset.filter(estat__in=[Tasca.Estat.PENDENT, Tasca.Estat.EN_CURS, Tasca.Estat.BLOQUEJADA])


def tasques_vencudes_queryset(queryset=None):
    return tasques_obertes_queryset(queryset).filter(data_limit__lt=timezone.localdate())


class ReunioListView(ReunionsBaseMixin, ListView):
    model = Reunio
    template_name = 'reunions/reunio_list.html'
    context_object_name = 'reunions'

    def get_queryset(self):
        qs = Reunio.objects.select_related('convocada_per', 'moderada_per', 'area').prefetch_related(
            'etiquetes',
            Prefetch('tasques_originades', queryset=tasques_obertes_queryset()),
        ).annotate(
            total_punts=Count('punts_ordre_dia', distinct=True),
            total_tasques_obertes=Count('tasques_originades', filter=Q(tasques_originades__estat__in=[Tasca.Estat.PENDENT, Tasca.Estat.EN_CURS, Tasca.Estat.BLOQUEJADA]), distinct=True),
        )
        q = (self.request.GET.get('q') or '').strip()
        if q:
            qs = qs.filter(Q(titol__icontains=q) | Q(descripcio__icontains=q) | Q(ubicacio__icontains=q))
        tipus = self.request.GET.get('tipus')
        if tipus in Reunio.Tipus.values:
            qs = qs.filter(tipus=tipus)
        estat = self.request.GET.get('estat')
        if estat in Reunio.Estat.values:
            qs = qs.filter(estat=estat)
        return qs.order_by('-inici', '-pk')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'tipus_options': Reunio.Tipus.choices,
            'estat_options': Reunio.Estat.choices,
            'current_filters': {'q': self.request.GET.get('q', ''), 'tipus': self.request.GET.get('tipus', ''), 'estat': self.request.GET.get('estat', '')},
            'reunions_obertes': Reunio.objects.filter(estat__in=[Reunio.Estat.PREPARACIO, Reunio.Estat.CONVOCADA]).count(),
            'reunions_celebrades': Reunio.objects.filter(estat__in=[Reunio.Estat.CELEBRADA, Reunio.Estat.TANCADA]).count(),
            'tasques_bloquejades': Tasca.objects.filter(estat=Tasca.Estat.BLOQUEJADA).count(),
            'tasques_vencudes': tasques_vencudes_queryset().count(),
        })
        return context


class ReunioDetailView(ReunionsBaseMixin, DetailView):
    model = Reunio
    template_name = 'reunions/reunio_detail.html'
    context_object_name = 'reunio'

    def get_queryset(self):
        return Reunio.objects.select_related('convocada_per', 'moderada_per', 'area', 'acte_agenda', 'acte_agenda__tipus').prefetch_related(
            'assistents', 'etiquetes', 'persones_relacionades', 'entitats_relacionades',
            'punts_ordre_dia__responsable', 'relacions_tasca__tasca__responsable', 'relacions_tasca__punt_ordre_dia',
            'acta__punts__punt_ordre_origen', 'acta__punts__tasques_generades__responsable',
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        reunio = context['reunio']
        acta = getattr(reunio, 'acta', None)
        reunio_url = self.request.build_absolute_uri(reunio.get_absolute_url())
        ordre_dia_share_url = self.request.build_absolute_uri(reunio.acte_agenda.get_absolute_url()) if reunio.acte_agenda else reunio_url
        ordre_export_url = self.request.build_absolute_uri(reverse('reunions:ordre_dia_export', kwargs={'pk': reunio.pk}))
        ordre_dia_text = generar_text_ordre_dia(reunio, share_url=ordre_dia_share_url)
        acta_text = generar_text_acta(acta) if acta else ''
        agenda_acte = reunio.acte_agenda
        agenda_confirmats = []
        agenda_potser = []
        agenda_no = []
        if agenda_acte:
            participants = list(agenda_acte.participants.select_related('usuari'))
            agenda_confirmats = [p for p in participants if p.intencio == 'HI_ANIRE']
            agenda_potser = [p for p in participants if p.intencio == 'POTSER']
            agenda_no = [p for p in participants if p.intencio == 'NO_HI_ANIRE']
        context.update({
            'punt_form': PuntOrdreDiaForm(),
            'acta_form': ActaForm(instance=acta, reunio=reunio) if acta else ActaForm(reunio=reunio, initial={'redactada_per': self.request.user}),
            'punt_acta_form': PuntActaForm(reunio=reunio),
            'tasca_rapida_form': TascaRapidaReunioForm(usuari=self.request.user),
            'tasques_relacionades': Tasca.objects.filter(relacions_reunio__reunio=reunio).select_related('responsable').distinct(),
            'tasques_obertes': tasques_obertes_queryset(Tasca.objects.filter(relacions_reunio__reunio=reunio)).select_related('responsable').distinct(),
            'tasques_proposades_ordre': Tasca.objects.filter(
                proposar_seguent_ordre_dia=True,
                estat__in=[Tasca.Estat.PENDENT, Tasca.Estat.EN_CURS, Tasca.Estat.BLOQUEJADA],
            ).exclude(relacions_reunio__reunio=reunio).select_related('responsable', 'reunio_origen').distinct()[:8],
            'ordre_dia_text': ordre_dia_text,
            'ordre_dia_text_url': quote(ordre_dia_text),
            'ordre_dia_share_url': ordre_dia_share_url,
            'ordre_dia_export_url': ordre_export_url,
            'ordre_dia_whatsapp_url': f'https://wa.me/?text={quote(ordre_dia_text)}',
            'ordre_dia_email_url': f'mailto:?subject=Ordre del dia · {quote(reunio.titol)}&body={quote(ordre_dia_text)}',
            'acta_text': acta_text,
            'acta_text_url': quote(acta_text) if acta_text else '',
            'acta_share_url': reunio_url,
            'acta_export_url': self.request.build_absolute_uri(reverse('reunions:acta_export', kwargs={'pk': reunio.pk})) if acta else '',
            'acta_whatsapp_url': f'https://wa.me/?text={quote(acta_text)}' if acta else '',
            'acta_email_url': f'mailto:?subject=Acta · {quote(reunio.titol)}&body={quote(acta_text)}' if acta else '',
            'acta': acta,
            'agenda_acte': agenda_acte,
            'agenda_confirmats': agenda_confirmats,
            'agenda_potser': agenda_potser,
            'agenda_no': agenda_no,
        })
        return context


class ReunioActaWorkspaceView(ReunionsBaseMixin, DetailView):
    model = Reunio
    template_name = 'reunions/acta_workspace.html'
    context_object_name = 'reunio'

    def get_queryset(self):
        return Reunio.objects.select_related('convocada_per', 'moderada_per', 'area').prefetch_related(
            'punts_ordre_dia',
            'acta__punts',
            'acta__punts__tasques_generades__responsable',
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        reunio = context['reunio']
        acta, _created = Acta.objects.get_or_create(
            reunio=reunio,
            defaults={'redactada_per': self.request.user},
        )
        sincronitzar_punts_acta_amb_ordre_dia(acta)
        acta_text = generar_text_acta(acta)
        reunio_url = self.request.build_absolute_uri(reunio.get_absolute_url())
        context.update({
            'acta': acta,
            'task_responsables': Usuari.objects.filter(is_active=True).only('id', 'nom_complet', 'username').order_by('nom_complet', 'username')[:80],
            'acta_text_url': quote(acta_text),
            'acta_text': acta_text,
            'acta_share_url': reunio_url,
            'acta_export_url': self.request.build_absolute_uri(reverse('reunions:acta_export', kwargs={'pk': reunio.pk})),
            'acta_whatsapp_url': f'https://wa.me/?text={quote(acta_text)}',
            'acta_email_url': f'mailto:?subject=Acta · {quote(reunio.titol)}&body={quote(acta_text)}',
        })
        return context


class ReunioCreateView(ReunioWritePermissionMixin, ReunionsBaseMixin, CreateView):
    model = Reunio
    form_class = ReunioForm
    template_name = 'reunions/reunio_form.html'

    def get_initial(self):
        initial = super().get_initial()
        initial['convocada_per'] = self.request.user
        initial['moderada_per'] = self.request.user
        return initial

    def form_valid(self, form):
        messages.success(self.request, 'Reunió creada correctament.')
        return super().form_valid(form)


class ReunioUpdateView(ReunioWritePermissionMixin, ReunionsBaseMixin, UpdateView):
    model = Reunio
    form_class = ReunioForm
    template_name = 'reunions/reunio_form.html'

    def form_valid(self, form):
        messages.success(self.request, 'Reunió actualitzada.')
        return super().form_valid(form)


class PuntOrdreDiaCreateView(ReunionsWritePermissionMixin, ReunionsBaseMixin, CreateView):
    permission_required = 'reunions.add_puntordredia'
    model = PuntOrdreDia
    form_class = PuntOrdreDiaForm

    def dispatch(self, request, *args, **kwargs):
        self.reunio = get_object_or_404(Reunio, pk=kwargs['pk'])
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.reunio = self.reunio
        form.instance.ordre = self.reunio.punts_ordre_dia.count() + 1
        response = super().form_valid(form)

        acta = getattr(self.reunio, 'acta', None)
        if acta:
            sincronitzats = sincronitzar_punts_acta_amb_ordre_dia(acta)
            if sincronitzats:
                messages.success(self.request, f'Punt de l’ordre del dia afegit i acta actualitzada amb {sincronitzats} punt(s).')
            else:
                messages.success(self.request, 'Punt de l’ordre del dia afegit.')
        else:
            messages.success(self.request, 'Punt de l’ordre del dia afegit.')

        return response

    def get_success_url(self):
        return reverse('reunions:reunio_detail', kwargs={'pk': self.reunio.pk}) + '#ordre-dia'


class PuntOrdreDiaUpdateView(ReunionsWritePermissionMixin, ReunionsBaseMixin, UpdateView):
    permission_required = 'reunions.change_puntordredia'
    model = PuntOrdreDia
    form_class = PuntOrdreDiaForm
    template_name = 'reunions/punt_ordre_form.html'

    def get_success_url(self):
        messages.success(self.request, 'Punt de l’ordre del dia actualitzat.')
        return reverse('reunions:reunio_detail', kwargs={'pk': self.object.reunio_id}) + '#ordre-dia'


class PuntOrdreDiaDeleteView(ReunionsWritePermissionMixin, ReunionsBaseMixin, TemplateView):
    permission_required = 'reunions.delete_puntordredia'

    def post(self, request, *args, **kwargs):
        punt = get_object_or_404(PuntOrdreDia, pk=kwargs['punt_pk'])
        reunio_id = punt.reunio_id
        punt.delete()
        messages.success(request, 'Punt de l’ordre del dia eliminat.')
        return redirect('reunions:reunio_detail', pk=reunio_id)


class PuntOrdreDiaMoveView(ReunionsWritePermissionMixin, ReunionsBaseMixin, TemplateView):
    permission_required = 'reunions.change_puntordredia'

    def post(self, request, *args, **kwargs):
        reunio = get_object_or_404(Reunio, pk=kwargs['pk'])
        direction = request.POST.get('direction')
        with transaction.atomic():
            punt = get_object_or_404(PuntOrdreDia.objects.select_for_update(), pk=kwargs['punt_pk'], reunio=reunio)
            neighbour_order = punt.ordre - 1 if direction == 'up' else punt.ordre + 1
            neighbour = reunio.punts_ordre_dia.select_for_update().filter(ordre=neighbour_order).first()
            if neighbour:
                ordre_original_punt = punt.ordre
                ordre_original_vei = neighbour.ordre
                ordre_temporal = (
                    reunio.punts_ordre_dia.select_for_update().aggregate(max_ordre=Max('ordre'))['max_ordre'] or 0
                ) + 1
                punt.ordre = ordre_temporal
                punt.save(update_fields=['ordre'])
                neighbour.ordre = ordre_original_punt
                neighbour.save(update_fields=['ordre'])
                punt.ordre = ordre_original_vei
                punt.save(update_fields=['ordre'])
                messages.success(request, 'Ordre del dia reordenat.')
            else:
                messages.info(request, 'Aquest punt ja és a la posició límit.')
        return redirect('reunions:reunio_detail', pk=reunio.pk)


class PuntOrdreDiaCreateFromTaskView(ReunionsWritePermissionMixin, ReunionsBaseMixin, TemplateView):
    permission_required = ('reunions.add_puntordredia', 'reunions.change_tasca')

    def post(self, request, *args, **kwargs):
        reunio = get_object_or_404(Reunio, pk=kwargs['pk'])
        tasca = get_object_or_404(Tasca, pk=kwargs['tasca_pk'])
        nou_ordre = reunio.punts_ordre_dia.count() + 1
        PuntOrdreDia.objects.create(
            reunio=reunio,
            ordre=nou_ordre,
            titol=tasca.titol,
            descripcio=tasca.motiu_proposta_ordre_dia or '',
            responsable=tasca.responsable,
            estat=PuntOrdreDia.Estat.PENDENT,
        )
        TascaRelacioReunio.objects.get_or_create(
            tasca=tasca,
            reunio=reunio,
            tipus_relacio=TascaRelacioReunio.TipusRelacio.PROPOSTA_ORDRE_DIA,
            defaults={'resum': 'Punt de l’ordre del dia generat des de la tasca proposada.'},
        )
        acta = getattr(reunio, 'acta', None)
        if acta:
            sincronitzats = sincronitzar_punts_acta_amb_ordre_dia(acta)
            if sincronitzats:
                messages.success(request, f'Punt creat a partir de la tasca i acta actualitzada amb {sincronitzats} punt(s).')
            else:
                messages.success(request, 'Punt creat a partir de la tasca marcada per al següent ordre del dia.')
        else:
            messages.success(request, 'Punt creat a partir de la tasca marcada per al següent ordre del dia.')
        return redirect('reunions:reunio_detail', pk=reunio.pk)


class ActaUpdateView(ReunionsWritePermissionMixin, ReunionsBaseMixin, UpdateView):
    permission_required = 'reunions.change_acta'
    model = Acta
    form_class = ActaForm
    template_name = 'reunions/acta_form.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['reunio'] = self.object.reunio
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, 'Acta actualitzada.')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('reunions:reunio_detail', kwargs={'pk': self.object.reunio_id}) + '#acta'


class ActaCreateOrUpdateView(ReunionsWritePermissionMixin, ReunionsBaseMixin, TemplateView):
    permission_required = ('reunions.add_acta', 'reunions.change_acta')

    def post(self, request, *args, **kwargs):
        reunio = get_object_or_404(Reunio, pk=kwargs['pk'])
        acta = getattr(reunio, 'acta', None)
        form = ActaForm(request.POST, instance=acta, reunio=reunio)
        if form.is_valid():
            acta = form.save(commit=False)
            acta.reunio = reunio
            acta.save()
            inicialitzades = inicialitzar_punts_acta_des_de_ordre_dia(acta)
            if inicialitzades:
                messages.success(request, f'Acta guardada i {inicialitzades} punts inicialitzats des de l’ordre del dia.')
            else:
                messages.success(request, 'Acta guardada correctament.')
        else:
            messages.error(request, 'Revisa els camps de l’acta.')
        return redirect('reunions:reunio_detail', pk=reunio.pk)


class PuntActaCreateView(ReunionsWritePermissionMixin, ReunionsBaseMixin, CreateView):
    permission_required = 'reunions.add_puntacta'
    model = PuntActa
    form_class = PuntActaForm

    def dispatch(self, request, *args, **kwargs):
        self.acta = get_object_or_404(Acta, pk=kwargs['acta_pk'])
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['reunio'] = self.acta.reunio
        return kwargs

    def form_valid(self, form):
        form.instance.acta = self.acta
        if not form.instance.ordre:
            form.instance.ordre = self.acta.punts.count() + 1
        messages.success(self.request, 'Punt d’acta afegit.')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('reunions:reunio_detail', kwargs={'pk': self.acta.reunio_id}) + '#acta'


class ReunioQuickTaskCreateView(TascaWritePermissionMixin, ReunionsBaseMixin, TemplateView):
    def post(self, request, *args, **kwargs):
        reunio = get_object_or_404(Reunio, pk=kwargs['pk'])
        acta = getattr(reunio, 'acta', None)
        form = TascaRapidaReunioForm(request.POST, usuari=request.user)
        if form.is_valid():
            tasca = form.save(commit=False)
            tasca.creada_per = request.user
            tasca.responsable = tasca.responsable or request.user
            tasca.origen = Tasca.Origen.REUNIO
            tasca.reunio_origen = reunio
            tasca.save()
            if acta and acta.punts.exists():
                ultim_punt = acta.punts.order_by('-ordre', '-pk').first()
                tasca.punt_acta_origen = ultim_punt
                tasca.save(update_fields=['punt_acta_origen'])
            TascaRelacioReunio.objects.get_or_create(
                tasca=tasca,
                reunio=reunio,
                punt_acta=tasca.punt_acta_origen,
                tipus_relacio=TascaRelacioReunio.TipusRelacio.ORIGEN,
                defaults={'resum': 'Tasca creada ràpidament des de la redacció de l’acta.'},
            )
            messages.success(request, 'Tasca ràpida afegida sense sortir de l’acta.')
        else:
            messages.error(request, 'No s’ha pogut crear la tasca ràpida. Revisa títol i prioritat.')
        return redirect('reunions:reunio_detail', pk=reunio.pk)


class ReunioOrdreDiaExportView(ReunionsBaseMixin, TemplateView):
    def get(self, request, *args, **kwargs):
        reunio = get_object_or_404(Reunio, pk=kwargs['pk'])
        text = generar_text_ordre_dia(reunio)
        filename = f'ordre-dia-reunio-{reunio.pk}.txt'
        response = HttpResponse(text, content_type='text/plain; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response


class ReunioActaExportView(ReunionsBaseMixin, TemplateView):
    def get(self, request, *args, **kwargs):
        reunio = get_object_or_404(Reunio, pk=kwargs['pk'])
        acta = get_object_or_404(Acta, reunio=reunio)
        text = generar_text_acta(acta)
        filename = f'acta-reunio-{reunio.pk}.txt'
        response = HttpResponse(text, content_type='text/plain; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response


class PuntActaUpdateView(ReunionsWritePermissionMixin, ReunionsBaseMixin, UpdateView):
    permission_required = 'reunions.change_puntacta'
    model = PuntActa
    form_class = PuntActaForm
    template_name = 'reunions/punt_acta_form.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['reunio'] = self.object.acta.reunio
        return kwargs

    def get_success_url(self):
        messages.success(self.request, 'Punt d’acta actualitzat.')
        return reverse('reunions:reunio_detail', kwargs={'pk': self.object.acta.reunio_id}) + '#acta'


class PuntActaQuickUpdateView(ReunionsWritePermissionMixin, ReunionsBaseMixin, TemplateView):
    permission_required = 'reunions.change_puntacta'

    def post(self, request, *args, **kwargs):
        punt = get_object_or_404(PuntActa, pk=kwargs['pk'])
        field = request.POST.get('field', '').strip()
        if field not in {'contingut', 'acords', 'titol'}:
            return JsonResponse({'ok': False, 'error': 'Camp no permès.'}, status=400)
        setattr(punt, field, request.POST.get('value', ''))
        punt.save(update_fields=[field, 'actualitzat_el'])
        return JsonResponse({'ok': True, 'updated': timezone.localtime(punt.actualitzat_el).strftime('%H:%M:%S')})


class PuntActaTaskQuickCreateView(TascaWritePermissionMixin, ReunionsBaseMixin, TemplateView):
    def post(self, request, *args, **kwargs):
        punt = get_object_or_404(PuntActa.objects.select_related('acta__reunio'), pk=kwargs['pk'])
        titol = (request.POST.get('titol') or '').strip()
        if not titol:
            return JsonResponse({'ok': False, 'error': 'Cal indicar un títol.'}, status=400)

        responsable = request.user
        responsable_id = request.POST.get('responsable_id')
        if responsable_id:
            responsable = Usuari.objects.filter(pk=responsable_id).first() or request.user

        prioritat = request.POST.get('prioritat')
        if prioritat not in Tasca.Prioritat.values:
            prioritat = Tasca.Prioritat.MITJANA

        data_limit = None
        data_limit_raw = (request.POST.get('data_limit') or '').strip()
        if data_limit_raw:
            try:
                data_limit = datetime.strptime(data_limit_raw, '%Y-%m-%d').date()
            except ValueError:
                return JsonResponse({'ok': False, 'error': 'Data límit no vàlida.'}, status=400)

        descripcio = (request.POST.get('descripcio') or '').strip()
        tasca = Tasca.objects.create(
            titol=titol,
            descripcio=descripcio,
            creada_per=request.user,
            responsable=responsable,
            prioritat=prioritat,
            data_limit=data_limit,
            origen=Tasca.Origen.PUNT_ACTA,
            reunio_origen=punt.acta.reunio,
            punt_acta_origen=punt,
        )
        TascaRelacioReunio.objects.get_or_create(
            tasca=tasca,
            reunio=punt.acta.reunio,
            punt_acta=punt,
            tipus_relacio=TascaRelacioReunio.TipusRelacio.ORIGEN,
            defaults={'resum': 'Tasca creada des del modal ràpid de la redacció de l’acta.'},
        )
        return JsonResponse({
            'ok': True,
            'task': {
                'id': tasca.pk,
                'title': tasca.titol,
                'status': tasca.get_estat_display(),
                'priority': tasca.get_prioritat_display(),
                'responsable': str(tasca.responsable),
                'url': reverse('reunions:tasca_detail', kwargs={'pk': tasca.pk}),
                'delete_url': reverse('reunions:tasca_delete', kwargs={'pk': tasca.pk}),
                'can_delete': can_delete_task(request.user, tasca),
            },
        })


class PuntActaTaskCommandCreateView(TascaWritePermissionMixin, ReunionsBaseMixin, TemplateView):
    def post(self, request, *args, **kwargs):
        punt = get_object_or_404(PuntActa.objects.select_related('acta__reunio'), pk=kwargs['pk'])
        content = request.POST.get('content') or ''
        parsed_lines = parse_task_commands(content)
        if not parsed_lines:
            return JsonResponse({'ok': False, 'error': 'No s’han detectat comandes @tasca.'}, status=400)

        users_by_username = {
            user.username.lower(): user
            for user in Usuari.objects.filter(is_active=True).only('id', 'username', 'nom_complet').order_by('nom_complet', 'username')
        }
        existing_signatures = {
            extract_task_command_signature(task.descripcio)
            for task in Tasca.objects.filter(punt_acta_origen=punt).only('descripcio')
        }
        created_tasks = []
        skipped_tasks = []
        errors = []
        for command in parsed_lines:
            if not command['title']:
                errors.append(f'Comanda sense títol: {command["raw"]}')
                continue
            signature = build_task_command_signature(command['raw'])
            if signature in existing_signatures:
                skipped_tasks.append(command['raw'])
                continue
            responsable = request.user
            if command['username']:
                responsable = users_by_username.get(command['username'].lower(), request.user)
            tasca = Tasca.objects.create(
                titol=command['title'],
                creada_per=request.user,
                responsable=responsable,
                prioritat=command['priority'] or Tasca.Prioritat.MITJANA,
                data_limit=command['due_date'],
                origen=Tasca.Origen.PUNT_ACTA,
                reunio_origen=punt.acta.reunio,
                punt_acta_origen=punt,
                descripcio=f'Creat automàticament des de comanda a l’acta: {command["raw"]}\n[@task-command:{signature}]',
            )
            existing_signatures.add(signature)
            TascaRelacioReunio.objects.get_or_create(
                tasca=tasca,
                reunio=punt.acta.reunio,
                punt_acta=punt,
                tipus_relacio=TascaRelacioReunio.TipusRelacio.ORIGEN,
                defaults={'resum': 'Tasca creada automàticament des d’una comanda @tasca.'},
            )
            created_tasks.append({
                'id': tasca.pk,
                'title': tasca.titol,
                'status': tasca.get_estat_display(),
                'priority': tasca.get_prioritat_display(),
                'responsable': str(tasca.responsable),
                'url': reverse('reunions:tasca_detail', kwargs={'pk': tasca.pk}),
                'delete_url': reverse('reunions:tasca_delete', kwargs={'pk': tasca.pk}),
                'can_delete': can_delete_task(request.user, tasca),
            })

        return JsonResponse({'ok': True, 'tasks': created_tasks, 'skipped': skipped_tasks, 'errors': errors})


class TascaListView(ReunionsBaseMixin, ListView):
    model = Tasca
    template_name = 'reunions/tasca_list.html'
    context_object_name = 'tasques'

    def get_queryset(self):
        qs = Tasca.objects.select_related('responsable', 'creada_per', 'area', 'reunio_origen', 'punt_acta_origen__acta__reunio').prefetch_related('collaboradors', 'etiquetes')
        search = (self.request.GET.get('q') or '').strip()
        if search:
            qs = qs.filter(Q(titol__icontains=search) | Q(descripcio__icontains=search) | Q(observacions_seguiment__icontains=search))
        for field, values in [('estat', Tasca.Estat.values), ('prioritat', Tasca.Prioritat.values), ('origen', Tasca.Origen.values)]:
            current = self.request.GET.get(field)
            if current in values:
                qs = qs.filter(**{field: current})
        if self.request.GET.get('vencudes') == '1':
            qs = tasques_vencudes_queryset(qs)
        if self.request.GET.get('bloquejades') == '1':
            qs = qs.filter(estat=Tasca.Estat.BLOQUEJADA)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'current_filters': {key: self.request.GET.get(key, '') for key in ['q', 'estat', 'prioritat', 'origen', 'vencudes', 'bloquejades']},
            'estat_options': Tasca.Estat.choices,
            'prioritat_options': Tasca.Prioritat.choices,
            'origen_options': Tasca.Origen.choices,
            'pendents_count': Tasca.objects.filter(estat=Tasca.Estat.PENDENT).count(),
            'bloquejades_count': Tasca.objects.filter(estat=Tasca.Estat.BLOQUEJADA).count(),
            'estrategiques_count': Tasca.objects.filter(es_estrategica=True).count(),
        })
        return context


class TascaDetailView(ReunionsBaseMixin, DetailView):
    model = Tasca
    template_name = 'reunions/tasca_detail.html'
    context_object_name = 'tasca'

    def get_queryset(self):
        return Tasca.objects.select_related('responsable', 'creada_per', 'area', 'reunio_origen', 'punt_acta_origen__acta__reunio').prefetch_related(
            'collaboradors', 'persones_relacionades', 'entitats_relacionades', 'etiquetes',
            'relacions_reunio__reunio', 'relacions_reunio__punt_ordre_dia', 'relacions_reunio__punt_acta',
            'seguiments__autor', 'seguiments__reunio', 'historic_estats__canviat_per',
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tasca = context['tasca']
        context.update({
            'seguiment_form': SeguimentTascaForm(tasca=tasca, autor=self.request.user),
            'relacio_form': TascaRelacioReunioForm(tasca=tasca),
            'can_delete_tasca': can_delete_task(self.request.user, tasca),
        })
        return context


class TascaCreateView(TascaWritePermissionMixin, ReunionsBaseMixin, CreateView):
    model = Tasca
    form_class = TascaForm
    template_name = 'reunions/tasca_form.html'

    def get_initial(self):
        initial = super().get_initial()
        initial['creada_per'] = self.request.user
        initial['responsable'] = self.request.user
        return initial

    def form_valid(self, form):
        messages.success(self.request, 'Tasca creada correctament.')
        return super().form_valid(form)


class TascaUpdateView(TascaWritePermissionMixin, ReunionsBaseMixin, UpdateView):
    model = Tasca
    form_class = TascaForm
    template_name = 'reunions/tasca_form.html'

    def form_valid(self, form):
        messages.success(self.request, 'Tasca actualitzada.')
        return super().form_valid(form)


class TascaDeleteView(LoginRequiredMixin, TemplateView):
    def post(self, request, *args, **kwargs):
        tasca = get_object_or_404(Tasca.objects.select_related('creada_per', 'punt_acta_origen__acta__reunio'), pk=kwargs['pk'])
        if not can_delete_task(request.user, tasca):
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'ok': False, 'error': 'No tens permisos per eliminar aquesta tasca.'}, status=403)
            return HttpResponseForbidden('No tens permisos per eliminar aquesta tasca.')

        tasca.delete()
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'ok': True})

        messages.success(request, 'Tasca eliminada.')
        next_url = request.POST.get('next') or request.META.get('HTTP_REFERER') or reverse('reunions:tasca_list')
        return redirect(next_url)


class SeguimentTascaCreateView(TascaWritePermissionMixin, ReunionsBaseMixin, TemplateView):
    def post(self, request, *args, **kwargs):
        tasca = get_object_or_404(Tasca, pk=kwargs['pk'])
        form = SeguimentTascaForm(request.POST, tasca=tasca, autor=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Seguiment afegit.')
        else:
            messages.error(request, 'No s’ha pogut afegir el seguiment.')
        return redirect('reunions:tasca_detail', pk=tasca.pk)


class TascaRelacioReunioCreateView(TascaWritePermissionMixin, ReunionsBaseMixin, TemplateView):
    def post(self, request, *args, **kwargs):
        tasca = get_object_or_404(Tasca, pk=kwargs['pk'])
        form = TascaRelacioReunioForm(request.POST, tasca=tasca)
        if form.is_valid():
            form.save()
            messages.success(request, 'Relació amb reunió registrada.')
        else:
            messages.error(request, 'No s’ha pogut registrar la relació amb la reunió.')
        return redirect('reunions:tasca_detail', pk=tasca.pk)


class SeguimentPanelView(ReunionsBaseMixin, TemplateView):
    template_name = 'reunions/panel_seguiment.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tasques = Tasca.objects.select_related('responsable', 'area', 'reunio_origen').prefetch_related('relacions_reunio__reunio')
        obertes = tasques_obertes_queryset(tasques)
        context.update({
            'tasques_obertes': obertes.order_by('data_limit', '-es_estrategica')[:10],
            'tasques_bloquejades': tasques.filter(estat=Tasca.Estat.BLOQUEJADA)[:10],
            'tasques_vencudes': tasques_vencudes_queryset(tasques).order_by('data_limit', '-es_estrategica')[:10],
            'seguiments_recents': SeguimentTasca.objects.select_related('tasca', 'autor', 'reunio')[:12],
            'reunions_amb_tasques_obertes': Reunio.objects.annotate(
                total_obertes=Count('relacions_tasca', filter=Q(relacions_tasca__tasca__estat__in=[Tasca.Estat.PENDENT, Tasca.Estat.EN_CURS, Tasca.Estat.BLOQUEJADA]), distinct=True)
            ).filter(total_obertes__gt=0).select_related('area')[:10],
        })
        return context


def generar_text_ordre_dia(reunio, share_url=''):
    lines = [
        reunio.titol,
        f"📅 {timezone.localtime(reunio.inici).strftime('%d/%m/%Y %H:%M')} h",
    ]
    if reunio.fi:
        lines.append(f"⏱️ Fins a les {timezone.localtime(reunio.fi).strftime('%H:%M')} h")
    if reunio.ubicacio:
        lines.append(f"📍 {reunio.ubicacio}")
    lines.extend(['', 'Ordre del dia', ''])
    for punt in reunio.punts_ordre_dia.order_by('ordre', 'pk'):
        lines.append(f'{punt.ordre}. {punt.titol}')
    if share_url:
        lines.extend(['', share_url])
    return '\n'.join(lines).strip()


def generar_text_acta(acta):
    lines = [f'Acta · {acta.reunio.titol}', '']
    for punt in acta.punts.order_by('ordre', 'pk'):
        lines.append(f'{punt.ordre}. {punt.titol}')
        if punt.contingut:
            lines.append(punt.contingut.strip())
        if punt.acords:
            lines.append(f'Acords: {punt.acords.strip()}')
        tasques = list(punt.tasques_generades.select_related('responsable').all())
        if tasques:
            lines.append('Tasques relacionades:')
            for index, tasca in enumerate(tasques, start=1):
                lines.append(f'{punt.ordre}.{index} - {tasca.titol} ({tasca.responsable})')
        lines.append('')
    return '\n'.join(lines).strip()


TASK_COMMAND_RE = re.compile(r'^\s*@tasca\b(?P<body>.+)$', flags=re.IGNORECASE)
TASK_COMMAND_SIGNATURE_RE = re.compile(r'\[@task-command:(?P<signature>[a-z0-9]+)\]')


def parse_task_commands(content):
    commands = []
    for line in (content or '').splitlines():
        match = TASK_COMMAND_RE.match(line.strip())
        if not match:
            continue
        body = match.group('body').strip()
        parts = [part.strip() for part in body.split('|')]
        title = parts[0] if parts else ''
        username = ''
        due_date = None
        priority = None
        for part in parts[1:]:
            if not part:
                continue
            if part.startswith('@') and len(part) > 1:
                username = part[1:]
                continue
            upper = part.upper()
            if upper in Tasca.Prioritat.values:
                priority = upper
                continue
            try:
                due_date = datetime.strptime(part, '%Y-%m-%d').date()
                continue
            except ValueError:
                pass
        commands.append({
            'raw': line.strip(),
            'title': title,
            'username': username,
            'due_date': due_date,
            'priority': priority,
        })
    return commands


def build_task_command_signature(raw_command):
    normalized = re.sub(r'\s+', ' ', (raw_command or '').strip().lower())
    return re.sub(r'[^a-z0-9]', '', normalized)


def extract_task_command_signature(description):
    match = TASK_COMMAND_SIGNATURE_RE.search(description or '')
    return match.group('signature') if match else ''


def can_delete_task(user, tasca):
    return (
        user.is_authenticated
        and (
            getattr(user, 'rol', None) == Usuari.Rol.ADMINISTRACIO
            or tasca.creada_per_id == user.id
        )
    )
