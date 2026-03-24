from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Case, Count, IntegerField, Q, Value, When
from django.utils import timezone
from django.views.generic import TemplateView

from agenda.models import Acte, ParticipacioActe, SegmentVisibilitat
from persones.models import Persona
from reunions.models import Reunio, Tasca
from usuaris.models import Usuari


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'core/dashboard.html'

    def _can_access_reunions(self):
        return self.request.user.rol in {Usuari.Rol.ADMINISTRACIO, Usuari.Rol.COORDINACIO}

    def _visible_actes_queryset(self):
        queryset = Acte.objects.select_related('tipus', 'creador').distinct()
        if self.request.user.has_perm('agenda.change_acte'):
            return queryset

        segments_filter = Q(ambit=SegmentVisibilitat.Ambit.ROL, codi=self.request.user.rol)
        if self.request.user.tipus:
            segments_filter |= Q(ambit=SegmentVisibilitat.Ambit.TIPUS, codi=self.request.user.tipus)
        user_segments = SegmentVisibilitat.objects.filter(segments_filter)
        return queryset.filter(estat=Acte.Estat.PUBLICAT).filter(
            Q(visible_per__isnull=True) | Q(visible_per__in=user_segments)
        ).distinct()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        now = timezone.now()
        today = timezone.localdate()
        user = self.request.user

        actes_visibles = self._visible_actes_queryset()
        propers_actes_qs = (
            actes_visibles.filter(inici__gte=now, estat=Acte.Estat.PUBLICAT)
            .annotate(
                prioritat_origen=Case(
                    When(creador=user, then=Value(0)),
                    When(external_source='', then=Value(1)),
                    default=Value(2),
                    output_field=IntegerField(),
                )
            )
            .order_by('prioritat_origen', '-es_important', 'inici')
        )
        propers_actes = propers_actes_qs[:8]

        participacions_meves = (
            ParticipacioActe.objects.filter(usuari=user, acte__inici__gte=now)
            .select_related('acte', 'acte__tipus')
            .order_by('acte__inici')[:6]
        )

        dashboard_data = {
            'can_access_reunions': self._can_access_reunions(),
            'propers_actes': propers_actes,
            'participacions_meves': participacions_meves,
            'actes_creats_per_mi': actes_visibles.filter(creador=user).count(),
            'actes_importats_visibles': actes_visibles.exclude(external_source='').count(),
            'total_actes_visibles': actes_visibles.count(),
            'propers_actes_total': propers_actes_qs.count(),
        }

        if self._can_access_reunions():
            futures_reunions = (
                Reunio.objects.filter(inici__gte=now)
                .filter(Q(assistents=user) | Q(convocada_per=user) | Q(moderada_per=user))
                .select_related('area', 'convocada_per', 'moderada_per')
                .order_by('inici')
                .distinct()[:6]
            )

            meves_tasques_qs = (
                Tasca.objects.filter(responsable=user)
                .exclude(estat__in=[Tasca.Estat.COMPLETADA, Tasca.Estat.CANCEL_LADA])
                .select_related('area', 'reunio_origen')
                .order_by('data_limit', '-es_estrategica', '-creat_el')
            )
            meves_tasques = meves_tasques_qs[:8]

            dashboard_data.update(
                {
                    'futures_reunions': futures_reunions,
                    'meves_tasques': meves_tasques,
                    'tasques_vencudes_meves': meves_tasques_qs.filter(data_limit__lt=today).count(),
                    'tasques_urgents_meves': meves_tasques_qs.filter(prioritat=Tasca.Prioritat.URGENT).count(),
                }
            )

        if user.rol == Usuari.Rol.ADMINISTRACIO:
            dashboard_data.update(
                {
                    'total_persones': Persona.objects.count(),
                    'usuaris_actius': Usuari.objects.filter(is_active=True).count(),
                    'usuaris_pendents': Usuari.objects.filter(is_active=False).count(),
                    'reunions_obertes': Reunio.objects.filter(
                        estat__in=[Reunio.Estat.PREPARACIO, Reunio.Estat.CONVOCADA]
                    ).count(),
                    'tasques_obertes': Tasca.objects.exclude(
                        estat__in=[Tasca.Estat.COMPLETADA, Tasca.Estat.CANCEL_LADA]
                    ).count(),
                    'tasques_bloquejades': Tasca.objects.filter(
                        estat=Tasca.Estat.BLOQUEJADA
                    ).count(),
                    'tasques_vencudes_globals': Tasca.objects.exclude(
                        estat__in=[Tasca.Estat.COMPLETADA, Tasca.Estat.CANCEL_LADA]
                    ).filter(data_limit__lt=today).count(),
                    'actes_publicats': Acte.objects.filter(estat=Acte.Estat.PUBLICAT).count(),
                    'actes_importats_total': Acte.objects.exclude(external_source='').count(),
                    'persones_sense_entitat': Persona.objects.annotate(
                        total_entitats=Count('entitats')
                    ).filter(total_entitats=0).count(),
                }
            )

        context.update(dashboard_data)
        return context

class AccessDeniedView(LoginRequiredMixin, TemplateView):
    template_name = 'core/access_denied.html'
