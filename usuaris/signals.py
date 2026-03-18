from django.contrib.auth.models import Group, Permission
from django.db.models.signals import post_migrate, post_save
from django.dispatch import receiver

from .models import Usuari

ROLE_GROUP_MAP = {
    Usuari.Rol.ADMINISTRADOR: 'Administrador',
    Usuari.Rol.COORDINADOR: 'Coordinador',
    Usuari.Rol.VOLUNTARI: 'Voluntari',
    Usuari.Rol.CONSULTA: 'Consulta',
}


@receiver(post_migrate)
def crear_groups_i_permisos(sender, **kwargs):
    configuracio = {
        'Administrador': [
            'add_acte', 'change_acte', 'delete_acte', 'view_acte',
            'add_participacioacte', 'change_participacioacte', 'view_participacioacte',
            'can_view_participants', 'can_mark_attendance',
        ],
        'Coordinador': [
            'add_acte', 'change_acte', 'view_acte',
            'view_participacioacte', 'can_view_participants', 'can_mark_attendance',
        ],
        'Voluntari': [
            'view_acte', 'add_participacioacte', 'change_participacioacte', 'view_participacioacte',
        ],
        'Consulta': ['view_acte'],
    }

    for nom_group, codenames in configuracio.items():
        group, _ = Group.objects.get_or_create(name=nom_group)
        permisos = Permission.objects.filter(codename__in=codenames)
        group.permissions.set(permisos)


@receiver(post_save, sender=Usuari)
def sync_user_role_group(sender, instance, **kwargs):
    target_group_name = ROLE_GROUP_MAP.get(instance.rol)
    instance.groups.clear()
    if target_group_name:
        group = Group.objects.filter(name=target_group_name).first()
        if group:
            instance.groups.add(group)
    is_admin = instance.rol == Usuari.Rol.ADMINISTRADOR
    updates = []
    if instance.is_staff != is_admin:
        instance.is_staff = is_admin
        updates.append('is_staff')
    if updates:
        instance.save(update_fields=updates)
