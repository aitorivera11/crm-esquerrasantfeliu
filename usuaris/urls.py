from django.urls import path

from .views import (
    CanviPasswordView,
    PerfilView,
    RegistreUsuariView,
    UsuariCreateView,
    UsuariDeleteView,
    UsuariListView,
    UsuariPasswordUpdateView,
    UsuariToggleActiveView,
    UsuariUpdateView,
)

urlpatterns = [
    path('registre/', RegistreUsuariView.as_view(), name='registre'),
    path('perfil/', PerfilView.as_view(), name='perfil'),
    path('perfil/contrasenya/', CanviPasswordView.as_view(), name='canvi_password'),
    path('admin/usuaris/', UsuariListView.as_view(), name='admin_usuari_list'),
    path('admin/usuaris/nou/', UsuariCreateView.as_view(), name='admin_usuari_create'),
    path('admin/usuaris/<int:pk>/editar/', UsuariUpdateView.as_view(), name='admin_usuari_update'),
    path('admin/usuaris/<int:pk>/password/', UsuariPasswordUpdateView.as_view(), name='admin_usuari_password'),
    path('admin/usuaris/<int:pk>/toggle-actiu/', UsuariToggleActiveView.as_view(), name='admin_usuari_toggle_active'),
    path('admin/usuaris/<int:pk>/eliminar/', UsuariDeleteView.as_view(), name='admin_usuari_delete'),
]
