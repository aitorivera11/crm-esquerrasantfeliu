from django.contrib.auth.models import Group, Permission
from django.db.models.signals import post_migrate
from django.dispatch import receiver


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
