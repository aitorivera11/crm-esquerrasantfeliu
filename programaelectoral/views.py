from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django.views.generic import TemplateView

from core.mixins import LoginRequiredMixin
from persones.models import Persona
from usuaris.models import Usuari

from .forms import (
    BlocProgramaForm,
    ComentariPropostaForm,
    ConvertirIdeaForm,
    IdeaPlujaForm,
    IdeaPublicaForm,
    PropostaForm,
)
from .models import BlocPrograma, ComentariProposta, IdeaPluja, IdeaPublica, Proposta


def _has_access(user):
    return user.is_authenticated and (
        user.rol in (Usuari.Rol.ADMINISTRACIO, Usuari.Rol.COORDINACIO)
        or user.has_perm('programaelectoral.manage_programa_electoral')
    )


class ProgramaPermissionMixin(LoginRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and not _has_access(request.user):
            raise PermissionDenied('No tens permisos per accedir al programa electoral.')
        return super().dispatch(request, *args, **kwargs)


# ── Tauler de control ──────────────────────────────────────────────────────────

class DashboardView(ProgramaPermissionMixin, TemplateView):
    template_name = 'programaelectoral/dashboard.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['total_blocs'] = BlocPrograma.objects.filter(pare__isnull=True).count()
        ctx['total_propostes'] = Proposta.objects.count()
        ctx['propostes_definitives'] = Proposta.objects.filter(estat=Proposta.Estat.DEFINITIVA).count()
        ctx['propostes_a_revisar'] = Proposta.objects.filter(estat=Proposta.Estat.A_REVISAR).count()
        ctx['total_idees'] = IdeaPluja.objects.count()
        ctx['idees_sense_proposta'] = IdeaPluja.objects.filter(proposta_associada__isnull=True).count()
        ctx['idees_publiques_pendents'] = IdeaPublica.objects.filter(processada=False).count()
        ctx['blocs_arrel'] = BlocPrograma.objects.filter(pare__isnull=True).prefetch_related('subblocs').order_by('ordre', 'titol')
        return ctx


# ── Estructura (Blocs) ─────────────────────────────────────────────────────────

@login_required
def estructura_view(request):
    if not _has_access(request.user):
        raise PermissionDenied
    blocs_arrel = BlocPrograma.objects.filter(pare__isnull=True).prefetch_related('subblocs__propostes').order_by('ordre', 'titol')
    return render(request, 'programaelectoral/estructura.html', {'blocs_arrel': blocs_arrel})


@login_required
def bloc_nou(request):
    if not _has_access(request.user):
        raise PermissionDenied
    form = BlocProgramaForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        bloc = form.save(commit=False)
        bloc.creat_per = request.user
        bloc.save()
        messages.success(request, f'Bloc "{bloc.titol}" creat correctament.')
        return redirect('programaelectoral:estructura')
    return render(request, 'programaelectoral/bloc_form.html', {'form': form, 'accio': 'Nou bloc'})


@login_required
def bloc_editar(request, pk):
    if not _has_access(request.user):
        raise PermissionDenied
    bloc = get_object_or_404(BlocPrograma, pk=pk)
    form = BlocProgramaForm(request.POST or None, instance=bloc)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f'Bloc "{bloc.titol}" actualitzat.')
        return redirect('programaelectoral:estructura')
    return render(request, 'programaelectoral/bloc_form.html', {'form': form, 'bloc': bloc, 'accio': 'Editar bloc'})


@login_required
@require_POST
def bloc_eliminar(request, pk):
    if not _has_access(request.user):
        raise PermissionDenied
    bloc = get_object_or_404(BlocPrograma, pk=pk)
    nom = bloc.titol
    bloc.delete()
    messages.success(request, f'Bloc "{nom}" eliminat.')
    return redirect('programaelectoral:estructura')


# ── Propostes ──────────────────────────────────────────────────────────────────

@login_required
def proposta_list(request):
    if not _has_access(request.user):
        raise PermissionDenied
    estat_filtre = request.GET.get('estat', '')
    bloc_filtre = request.GET.get('bloc', '')
    qs = Proposta.objects.select_related('bloc', 'creat_per').prefetch_related('comentaris')
    if estat_filtre:
        qs = qs.filter(estat=estat_filtre)
    if bloc_filtre:
        qs = qs.filter(bloc_id=bloc_filtre)
    blocs = BlocPrograma.objects.order_by('ordre', 'titol')
    return render(request, 'programaelectoral/proposta_list.html', {
        'propostes': qs,
        'blocs': blocs,
        'estat_filtre': estat_filtre,
        'bloc_filtre': bloc_filtre,
        'estats': Proposta.Estat.choices,
    })


@login_required
def proposta_nou(request):
    if not _has_access(request.user):
        raise PermissionDenied
    form = PropostaForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        proposta = form.save(commit=False)
        proposta.creat_per = request.user
        proposta.save()
        messages.success(request, f'Proposta "{proposta.titol}" creada.')
        return redirect('programaelectoral:proposta_detail', pk=proposta.pk)
    return render(request, 'programaelectoral/proposta_form.html', {'form': form, 'accio': 'Nova proposta'})


@login_required
def proposta_detail(request, pk):
    if not _has_access(request.user):
        raise PermissionDenied
    proposta = get_object_or_404(
        Proposta.objects.select_related('bloc', 'creat_per').prefetch_related('comentaris__autor', 'idees_origen'),
        pk=pk,
    )
    comentari_form = ComentariPropostaForm()
    return render(request, 'programaelectoral/proposta_detail.html', {
        'proposta': proposta,
        'comentari_form': comentari_form,
        'estats': Proposta.Estat.choices,
    })


@login_required
def proposta_editar(request, pk):
    if not _has_access(request.user):
        raise PermissionDenied
    proposta = get_object_or_404(Proposta, pk=pk)
    form = PropostaForm(request.POST or None, instance=proposta)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Proposta actualitzada.')
        return redirect('programaelectoral:proposta_detail', pk=proposta.pk)
    return render(request, 'programaelectoral/proposta_form.html', {
        'form': form,
        'proposta': proposta,
        'accio': 'Editar proposta',
    })


@login_required
@require_POST
def proposta_canviar_estat(request, pk):
    if not _has_access(request.user):
        raise PermissionDenied
    proposta = get_object_or_404(Proposta, pk=pk)
    nou_estat = request.POST.get('estat')
    estats_valids = {k for k, _ in Proposta.Estat.choices}
    if nou_estat in estats_valids:
        proposta.estat = nou_estat
        proposta.save(update_fields=['estat', 'actualitzat_el'])
        if request.headers.get('HX-Request'):
            return render(request, 'programaelectoral/components/proposta_estat_badge.html', {'proposta': proposta})
    return redirect('programaelectoral:proposta_detail', pk=pk)


@login_required
@require_POST
def proposta_comentar(request, pk):
    if not _has_access(request.user):
        raise PermissionDenied
    proposta = get_object_or_404(Proposta, pk=pk)
    form = ComentariPropostaForm(request.POST)
    if form.is_valid():
        comentari = form.save(commit=False)
        comentari.proposta = proposta
        comentari.autor = request.user
        comentari.save()
        if request.headers.get('HX-Request'):
            comentaris = proposta.comentaris.select_related('autor').all()
            return render(request, 'programaelectoral/components/comentaris_list.html', {
                'proposta': proposta,
                'comentaris': comentaris,
                'comentari_form': ComentariPropostaForm(),
            })
    return redirect('programaelectoral:proposta_detail', pk=pk)


# ── Pluja d'idees ──────────────────────────────────────────────────────────────

@login_required
def idea_list(request):
    if not _has_access(request.user):
        raise PermissionDenied
    font_filtre = request.GET.get('font', '')
    qs = IdeaPluja.objects.select_related('font_reunio', 'font_entitat', 'font_persona', 'proposta_associada', 'creat_per')
    if font_filtre:
        qs = qs.filter(font=font_filtre)
    return render(request, 'programaelectoral/idea_list.html', {
        'idees': qs,
        'font_filtre': font_filtre,
        'fonts': IdeaPluja.Font.choices,
    })


@login_required
def idea_nou(request):
    if not _has_access(request.user):
        raise PermissionDenied
    form = IdeaPlujaForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        idea = form.save(commit=False)
        idea.creat_per = request.user
        idea.save()
        messages.success(request, f'Idea "{idea.titol}" afegida a la pluja d\'idees.')
        return redirect('programaelectoral:idea_list')
    return render(request, 'programaelectoral/idea_form.html', {'form': form, 'accio': 'Nova idea'})


@login_required
def idea_detail(request, pk):
    if not _has_access(request.user):
        raise PermissionDenied
    idea = get_object_or_404(
        IdeaPluja.objects.select_related('font_reunio', 'font_entitat', 'font_persona', 'proposta_associada', 'creat_per'),
        pk=pk,
    )
    return render(request, 'programaelectoral/idea_detail.html', {'idea': idea})


@login_required
def idea_convertir(request, pk):
    if not _has_access(request.user):
        raise PermissionDenied
    idea = get_object_or_404(IdeaPluja, pk=pk)
    initial = {'titol': idea.titol, 'contingut': idea.descripcio}
    form = ConvertirIdeaForm(request.POST or None, initial=initial)
    if request.method == 'POST' and form.is_valid():
        proposta = Proposta.objects.create(
            titol=form.cleaned_data['titol'],
            contingut=form.cleaned_data['contingut'],
            bloc=form.cleaned_data['bloc'],
            estat=form.cleaned_data['estat'],
            creat_per=request.user,
        )
        idea.proposta_associada = proposta
        idea.save(update_fields=['proposta_associada', 'actualitzat_el'])
        messages.success(request, f'Idea convertida en proposta "{proposta.titol}".')
        return redirect('programaelectoral:proposta_detail', pk=proposta.pk)
    return render(request, 'programaelectoral/idea_convertir.html', {'form': form, 'idea': idea})


# ── Idees públiques ────────────────────────────────────────────────────────────

@login_required
def idees_publiques_list(request):
    if not _has_access(request.user):
        raise PermissionDenied
    qs = IdeaPublica.objects.select_related('persona_identificada', 'idea_pluja_resultant')
    processades = request.GET.get('processades', '')
    if processades == '1':
        qs = qs.filter(processada=True)
    elif processades == '0':
        qs = qs.filter(processada=False)
    return render(request, 'programaelectoral/idees_publiques_list.html', {
        'idees_publiques': qs,
        'processades': processades,
    })


@login_required
@require_POST
def idea_publica_processar(request, pk):
    if not _has_access(request.user):
        raise PermissionDenied
    idea_publica = get_object_or_404(IdeaPublica, pk=pk)
    idea_pluja = IdeaPluja.objects.create(
        titol=idea_publica.idea[:200] or '(sense títol)',
        descripcio=idea_publica.idea,
        font=IdeaPluja.Font.FORMULARI_PUBLIC,
        font_persona=idea_publica.persona_identificada,
        creat_per=request.user,
    )
    idea_publica.processada = True
    idea_publica.idea_pluja_resultant = idea_pluja
    idea_publica.save(update_fields=['processada', 'idea_pluja_resultant', 'actualitzat_el'])
    messages.success(request, "Idea pública afegida a la pluja d'idees.")
    return redirect('programaelectoral:idees_publiques_list')


# ── Formulari públic (sense autenticació) ─────────────────────────────────────

def formulari_public(request):
    form = IdeaPublicaForm(request.POST or None)
    success = False
    if request.method == 'POST' and form.is_valid():
        idea_publica = form.save(commit=False)
        persona_id = form.cleaned_data.get('persona_existent_id')
        if persona_id:
            persona = Persona.objects.filter(pk=persona_id).first()
            if persona:
                idea_publica.persona_identificada = persona
        elif idea_publica.nom or idea_publica.email or idea_publica.telefon:
            persona = None
            if idea_publica.email:
                persona, _ = Persona.objects.get_or_create(
                    email=idea_publica.email,
                    defaults={'nom': idea_publica.nom, 'telefon': idea_publica.telefon},
                )
            elif idea_publica.nom:
                persona = Persona.objects.create(
                    nom=idea_publica.nom,
                    telefon=idea_publica.telefon,
                )
            if persona:
                idea_publica.persona_identificada = persona
        idea_publica.save()
        success = True
        form = IdeaPublicaForm()
    return render(request, 'programaelectoral/formulari_public.html', {'form': form, 'success': success})


def formulari_cerca_persona(request):
    """Endpoint HTMX: cerca persones per nom al formulari públic."""
    q = request.GET.get('q', '').strip()
    persones = []
    if len(q) >= 2:
        persones = list(Persona.objects.filter(nom__icontains=q).values('id', 'nom', 'email')[:8])
    return render(request, 'programaelectoral/components/cerca_persona_resultat.html', {
        'persones': persones,
        'q': q,
    })
