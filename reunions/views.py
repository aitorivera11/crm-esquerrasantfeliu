from urllib.parse import quote

from django.contrib import messages
from django.db import transaction
from django.db.models import Count, Max, Prefetch, Q
from django.http import HttpResponse
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
)
from .models import Acta, PuntActa, PuntOrdreDia, Reunio, SeguimentTasca, Tasca, TascaRelacioReunio


class ReunionsPermissionMixin(RoleRequiredMixin):
    allowed_roles = (Usuari.Rol.ADMINISTRACIO, Usuari.Rol.COORDINACIO)


class ReunionsBaseMixin(ReunionsPermissionMixin):
    def get_success_url(self):
        return self.object.get_absolute_url()


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
        return qs

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
        ordre_dia_text = generar_text_ordre_dia(reunio)
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
            'acta_text': acta_text,
            'acta_text_url': quote(acta_text) if acta_text else '',
            'acta': acta,
            'agenda_acte': agenda_acte,
            'agenda_confirmats': agenda_confirmats,
            'agenda_potser': agenda_potser,
            'agenda_no': agenda_no,
        })
        return context


class ReunioCreateView(ReunionsBaseMixin, CreateView):
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


class ReunioUpdateView(ReunionsBaseMixin, UpdateView):
    model = Reunio
    form_class = ReunioForm
    template_name = 'reunions/reunio_form.html'

    def form_valid(self, form):
        messages.success(self.request, 'Reunió actualitzada.')
        return super().form_valid(form)


class PuntOrdreDiaCreateView(ReunionsBaseMixin, CreateView):
    model = PuntOrdreDia
    form_class = PuntOrdreDiaForm

    def dispatch(self, request, *args, **kwargs):
        self.reunio = get_object_or_404(Reunio, pk=kwargs['pk'])
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.reunio = self.reunio
        form.instance.ordre = self.reunio.punts_ordre_dia.count() + 1
        messages.success(self.request, 'Punt de l’ordre del dia afegit.')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('reunions:reunio_detail', kwargs={'pk': self.reunio.pk}) + '#ordre-dia'


class PuntOrdreDiaUpdateView(ReunionsBaseMixin, UpdateView):
    model = PuntOrdreDia
    form_class = PuntOrdreDiaForm
    template_name = 'reunions/punt_ordre_form.html'

    def get_success_url(self):
        messages.success(self.request, 'Punt de l’ordre del dia actualitzat.')
        return reverse('reunions:reunio_detail', kwargs={'pk': self.object.reunio_id}) + '#ordre-dia'


class PuntOrdreDiaDeleteView(ReunionsBaseMixin, TemplateView):
    def post(self, request, *args, **kwargs):
        punt = get_object_or_404(PuntOrdreDia, pk=kwargs['punt_pk'])
        reunio_id = punt.reunio_id
        punt.delete()
        messages.success(request, 'Punt de l’ordre del dia eliminat.')
        return redirect('reunions:reunio_detail', pk=reunio_id)


class PuntOrdreDiaMoveView(ReunionsBaseMixin, TemplateView):
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


class PuntOrdreDiaCreateFromTaskView(ReunionsBaseMixin, TemplateView):
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
        messages.success(request, 'Punt creat a partir de la tasca marcada per al següent ordre del dia.')
        return redirect('reunions:reunio_detail', pk=reunio.pk)


class ActaUpdateView(ReunionsBaseMixin, UpdateView):
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


class ActaCreateOrUpdateView(ReunionsBaseMixin, TemplateView):
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


class PuntActaCreateView(ReunionsBaseMixin, CreateView):
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


class ReunioQuickTaskCreateView(ReunionsBaseMixin, TemplateView):
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


class PuntActaUpdateView(ReunionsBaseMixin, UpdateView):
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
        })
        return context


class TascaCreateView(ReunionsBaseMixin, CreateView):
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


class TascaUpdateView(ReunionsBaseMixin, UpdateView):
    model = Tasca
    form_class = TascaForm
    template_name = 'reunions/tasca_form.html'

    def form_valid(self, form):
        messages.success(self.request, 'Tasca actualitzada.')
        return super().form_valid(form)


class SeguimentTascaCreateView(ReunionsBaseMixin, TemplateView):
    def post(self, request, *args, **kwargs):
        tasca = get_object_or_404(Tasca, pk=kwargs['pk'])
        form = SeguimentTascaForm(request.POST, tasca=tasca, autor=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Seguiment afegit.')
        else:
            messages.error(request, 'No s’ha pogut afegir el seguiment.')
        return redirect('reunions:tasca_detail', pk=tasca.pk)


class TascaRelacioReunioCreateView(ReunionsBaseMixin, TemplateView):
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


def generar_text_ordre_dia(reunio):
    lines = [f'Ordre del dia · {reunio.titol}', '']
    for punt in reunio.punts_ordre_dia.order_by('ordre', 'pk'):
        lines.append(f'{punt.ordre}. {punt.titol}')
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
