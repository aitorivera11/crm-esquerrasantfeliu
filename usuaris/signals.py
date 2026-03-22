from django.contrib.auth.models import Group, Permission
from django.db.models.signals import post_migrate, post_save
from django.dispatch import receiver

from .models import Usuari


GROUP_ADMINISTRACIO = 'Administració'
GROUP_COORDINACIO = 'Coordinació'
GROUP_PARTICIPANT = 'Participant'

ROLE_GROUP_MAP = {
    Usuari.Rol.ADMINISTRACIO: GROUP_ADMINISTRACIO,
    Usuari.Rol.COORDINACIO: GROUP_COORDINACIO,
    Usuari.Rol.PARTICIPANT: GROUP_PARTICIPANT,
}

LEGACY_GROUP_NAMES = {
    'Administrador': GROUP_ADMINISTRACIO,
    'Administracio': GROUP_ADMINISTRACIO,
    'Coordinador': GROUP_COORDINACIO,
    'Voluntari': GROUP_PARTICIPANT,
    'Consulta': GROUP_PARTICIPANT,
}


def _rename_legacy_groups():
    for legacy_name, target_name in LEGACY_GROUP_NAMES.items():
        legacy_group = Group.objects.filter(name=legacy_name).first()
        if not legacy_group:
            continue
        target_group, created = Group.objects.get_or_create(name=target_name)
        if created:
            legacy_group.name = target_name
            legacy_group.save(update_fields=['name'])
            target_group.delete()
            continue
        target_group.permissions.add(*legacy_group.permissions.all())
        for user in legacy_group.user_set.all():
            user.groups.add(target_group)
        legacy_group.delete()


@receiver(post_migrate)
def crear_groups_i_permisos(sender, **kwargs):
    _rename_legacy_groups()

    configuracio = {
        GROUP_ADMINISTRACIO: [
            'add_acte',
            'change_acte',
            'delete_acte',
            'view_acte',
            'add_participacioacte',
            'change_participacioacte',
            'delete_participacioacte',
            'view_participacioacte',
            'can_view_participants',
            'can_mark_attendance',
            'add_entitat',
            'change_entitat',
            'delete_entitat',
            'view_entitat',
            'view_persona',
            'add_persona',
            'change_persona',
            'delete_persona',
        ],
        GROUP_COORDINACIO: [
            'add_acte',
            'change_acte',
            'view_acte',
            'view_participacioacte',
            'can_view_participants',
            'can_mark_attendance',
            'add_entitat',
            'change_entitat',
            'delete_entitat',
            'view_entitat',
            'view_persona',
            'add_persona',
            'change_persona',
            'delete_persona',
        ],
        GROUP_PARTICIPANT: [
            'view_acte',
            'add_participacioacte',
            'change_participacioacte',
            'view_participacioacte',
        ],
    }

    for nom_group, codenames in configuracio.items():
        group, _ = Group.objects.get_or_create(name=nom_group)
        permisos = Permission.objects.filter(codename__in=codenames)
        group.permissions.set(permisos)


@receiver(post_save, sender=Usuari)
def sync_user_role_group(sender, instance, **kwargs):
    normalized_role = Usuari.Rol.normalize(instance.rol)
    if instance.rol != normalized_role:
        instance.rol = normalized_role
        Usuari.objects.filter(pk=instance.pk).update(rol=normalized_role)

    target_group_name = ROLE_GROUP_MAP.get(instance.rol)
    managed_group_names = list(ROLE_GROUP_MAP.values())
    managed_groups = Group.objects.filter(name__in=managed_group_names)

    if managed_groups.exists():
        instance.groups.remove(*managed_groups)

    if target_group_name:
        group, _ = Group.objects.get_or_create(name=target_group_name)
        instance.groups.add(group)

    is_admin = instance.rol == Usuari.Rol.ADMINISTRACIO

    updates = {}
    if instance.is_staff != is_admin:
        updates['is_staff'] = is_admin

    if updates:
        Usuari.objects.filter(pk=instance.pk).update(**updates)
        for field, value in updates.items():
            setattr(instance, field, value)
