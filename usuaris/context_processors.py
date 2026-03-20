from .models import Usuari


def pending_registrations(request):
    pending_count = 0
    if request.user.is_authenticated and request.user.rol == Usuari.Rol.ADMINISTRADOR:
        pending_count = Usuari.objects.filter(is_active=False).count()
    return {'pending_user_registrations': pending_count}
