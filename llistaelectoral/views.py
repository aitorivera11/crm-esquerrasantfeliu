import json

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST
from django.views.generic import TemplateView

from core.mixins import LoginRequiredMixin
from persones.models import Persona
from usuaris.models import Usuari

from .models import Candidatura, IntegrantLlista, PermisLlistaElectoral, PosicioLlista


class LlistaPermissionMixin(LoginRequiredMixin):
    permission_denied_message = 'No tens permisos per gestionar la llista electoral.'

    def dispatch(self, request, *args, **kwargs):
        user = request.user
        allowed = user.rol == Usuari.Rol.ADMINISTRACIO or PermisLlistaElectoral.objects.filter(user=user).exists()
        if not allowed:
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied(self.permission_denied_message)
        return super().dispatch(request, *args, **kwargs)


class LlistaElectoralView(LlistaPermissionMixin, TemplateView):
    template_name = 'llistaelectoral/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        candidatura, _ = Candidatura.objects.get_or_create(activa=True, defaults={'nom': 'Municipals 2027'})
        for numero in range(PosicioLlista.MIN_POSICIO, PosicioLlista.MAX_POSICIO + 1):
            PosicioLlista.objects.get_or_create(candidatura=candidatura, numero=numero)

        posicions = list(
            candidatura.posicions.select_related('integrant__persona', 'integrant__usuari').order_by('numero')
        )
        context['candidatura'] = candidatura
        context['posicions_titulars'] = [p for p in posicions if p.es_titular]
        context['posicions_suplents'] = [p for p in posicions if not p.es_titular]
        context['repositori'] = candidatura.integrants.filter(posicio__isnull=True).select_related('persona', 'usuari').order_by('creat_el')
        context['persones'] = Persona.objects.order_by('nom')
        context['usuaris'] = Usuari.objects.order_by('nom_complet', 'username')
        context['afiliacions'] = IntegrantLlista.Afiliacio.choices
        context['estats'] = IntegrantLlista.Estat.choices
        return context


def _has_access(user):
    return user.is_authenticated and (
        user.rol == Usuari.Rol.ADMINISTRACIO
        or PermisLlistaElectoral.objects.filter(user=user).exists()
    )


@login_required
@require_POST
def crear_integrant(request):
    if not _has_access(request.user):
        return JsonResponse({'ok': False, 'error': 'No autoritzat.'}, status=403)

    payload = json.loads(request.body or '{}')
    candidatura = Candidatura.objects.filter(activa=True).first() or Candidatura.objects.create(nom='Municipals 2027', activa=True)
    persona = Persona.objects.filter(pk=payload.get('persona_id')).first() if payload.get('persona_id') else None
    usuari = Usuari.objects.filter(pk=payload.get('usuari_id')).first() if payload.get('usuari_id') else None

    if not persona and not usuari:
        return JsonResponse({'ok': False, 'error': 'Selecciona una persona o un usuari.'}, status=400)

    integrant, created = IntegrantLlista.objects.get_or_create(
        candidatura=candidatura,
        persona=persona,
        usuari=usuari,
        defaults={
            'afiliacio': payload.get('afiliacio') or IntegrantLlista.Afiliacio.ESQUERRA,
            'estat': payload.get('estat') or IntegrantLlista.Estat.IDEA,
        },
    )
    if not created:
        integrant.afiliacio = payload.get('afiliacio') or integrant.afiliacio
        integrant.estat = payload.get('estat') or integrant.estat
        integrant.save(update_fields=['afiliacio', 'estat', 'actualitzat_el'])

    return JsonResponse({'ok': True, 'id': integrant.pk, 'nom': integrant.nom_mostrat})


@login_required
@require_POST
def editar_integrant(request, pk):
    if not _has_access(request.user):
        return JsonResponse({'ok': False, 'error': 'No autoritzat.'}, status=403)

    payload = json.loads(request.body or '{}')
    integrant = get_object_or_404(IntegrantLlista, pk=pk)
    allowed_af = {k for k, _ in IntegrantLlista.Afiliacio.choices}
    allowed_es = {k for k, _ in IntegrantLlista.Estat.choices}

    if payload.get('afiliacio') in allowed_af:
        integrant.afiliacio = payload['afiliacio']
    if payload.get('estat') in allowed_es:
        integrant.estat = payload['estat']
    integrant.save(update_fields=['afiliacio', 'estat', 'actualitzat_el'])

    return JsonResponse({'ok': True})


@login_required
@require_POST
def assignar_posicio(request):
    if not _has_access(request.user):
        return JsonResponse({'ok': False, 'error': 'No autoritzat.'}, status=403)

    payload = json.loads(request.body or '{}')
    candidatura = Candidatura.objects.filter(activa=True).first()
    if not candidatura:
        return JsonResponse({'ok': False, 'error': 'No hi ha candidatura activa.'}, status=400)

    with transaction.atomic():
        target = get_object_or_404(PosicioLlista, candidatura=candidatura, numero=payload.get('target_position'))
        source_num = payload.get('source_position')
        integrant = get_object_or_404(IntegrantLlista, candidatura=candidatura, pk=payload.get('integrant_id'))

        source = None
        if source_num:
            source = PosicioLlista.objects.select_for_update().filter(candidatura=candidatura, numero=source_num).first()

        target = PosicioLlista.objects.select_for_update().get(pk=target.pk)
        previous_target_integrant = target.integrant

        if source:
            source.integrant = None
            source.save(update_fields=['integrant', 'actualitzat_el'])

        target.integrant = None
        target.save(update_fields=['integrant', 'actualitzat_el'])

        if source and previous_target_integrant:
            source.integrant = previous_target_integrant
            source.save(update_fields=['integrant', 'actualitzat_el'])

        target.integrant = integrant
        target.save(update_fields=['integrant', 'actualitzat_el'])

    return JsonResponse({'ok': True})
