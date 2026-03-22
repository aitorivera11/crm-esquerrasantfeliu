from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone
from django.views.generic import TemplateView

from agenda.models import Acte
from persones.models import Persona
from usuaris.models import Usuari


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'core/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        propers_actes = Acte.objects.filter(inici__gte=timezone.now(), estat=Acte.Estat.PUBLICAT).order_by('-es_important', 'inici')[:5]
        context.update(
            {
                'total_actes': Acte.objects.count(),
                'actes_publicats': Acte.objects.filter(estat=Acte.Estat.PUBLICAT).count(),
                'propers_actes': propers_actes,
                'total_persones': Persona.objects.count(),
                'usuaris_actius': Usuari.objects.filter(is_active=True).count(),
            }
        )
        return context


class AccessDeniedView(LoginRequiredMixin, TemplateView):
    template_name = 'core/access_denied.html'
