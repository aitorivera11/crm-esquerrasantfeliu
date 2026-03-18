from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied

from usuaris.models import Usuari


class RoleRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    allowed_roles = ()
    permission_denied_message = 'No tens permisos per accedir a aquesta secció.'

    def test_func(self):
        user = self.request.user
        return user.is_authenticated and user.rol in self.allowed_roles

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            raise PermissionDenied(self.permission_denied_message)
        return super().handle_no_permission()


class AdminRequiredMixin(RoleRequiredMixin):
    allowed_roles = (Usuari.Rol.ADMINISTRADOR,)
