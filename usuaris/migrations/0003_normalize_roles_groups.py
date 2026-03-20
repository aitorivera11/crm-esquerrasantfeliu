from django.db import migrations, models


LEGACY_ROLE_MAP = {
    'ADMINISTRADOR': 'ADMINISTRACIO',
    'COORDINADOR': 'COORDINACIO',
    'VOLUNTARI': 'PARTICIPANT',
    'CONSULTA': 'PARTICIPANT',
}

LEGACY_GROUP_MAP = {
    'Administrador': 'Administració',
    'Administracio': 'Administració',
    'Coordinador': 'Coordinació',
    'Voluntari': 'Participant',
    'Consulta': 'Participant',
}

LEGACY_SEGMENT_MAP = {
    'ADMINISTRADOR': ('ADMINISTRACIO', 'Administració'),
    'COORDINADOR': ('COORDINACIO', 'Coordinació'),
    'VOLUNTARI': ('PARTICIPANT', 'Participant'),
    'CONSULTA': ('PARTICIPANT', 'Participant'),
}


def normalize_roles_groups_and_segments(apps, schema_editor):
    Usuari = apps.get_model('usuaris', 'Usuari')
    Group = apps.get_model('auth', 'Group')
    SegmentVisibilitat = apps.get_model('agenda', 'SegmentVisibilitat')

    for legacy_role, normalized_role in LEGACY_ROLE_MAP.items():
        Usuari.objects.filter(rol=legacy_role).update(rol=normalized_role)

    for legacy_name, target_name in LEGACY_GROUP_MAP.items():
        legacy_group = Group.objects.filter(name=legacy_name).first()
        if not legacy_group:
            continue
        target_group = Group.objects.filter(name=target_name).first()
        if target_group and target_group.pk != legacy_group.pk:
            target_group.permissions.add(*legacy_group.permissions.all())
            for user in legacy_group.user_set.all():
                user.groups.add(target_group)
            legacy_group.delete()
            continue
        legacy_group.name = target_name
        legacy_group.save(update_fields=['name'])

    for legacy_code, (normalized_code, label) in LEGACY_SEGMENT_MAP.items():
        legacy_segment = SegmentVisibilitat.objects.filter(ambit='ROL', codi=legacy_code).first()
        normalized_segment = SegmentVisibilitat.objects.filter(ambit='ROL', codi=normalized_code).first()
        if legacy_segment and normalized_segment and legacy_segment.pk != normalized_segment.pk:
            for acte in legacy_segment.actes_visibles.all():
                acte.visible_per.add(normalized_segment)
            for acte in legacy_segment.actes_assistencia.all():
                acte.assistencia_permesa_per.add(normalized_segment)
            legacy_segment.delete()
            continue
        if legacy_segment:
            legacy_segment.codi = normalized_code
            legacy_segment.etiqueta = label
            legacy_segment.save(update_fields=['codi', 'etiqueta'])

    role_group_map = {
        'ADMINISTRACIO': 'Administració',
        'COORDINACIO': 'Coordinació',
        'PARTICIPANT': 'Participant',
    }
    managed_groups = list(Group.objects.filter(name__in=role_group_map.values()))
    for user in Usuari.objects.all():
        if managed_groups:
            user.groups.remove(*managed_groups)
        target_group = Group.objects.filter(name=role_group_map.get(user.rol)).first()
        if target_group:
            user.groups.add(target_group)
        is_admin = user.rol == 'ADMINISTRACIO'
        if user.is_staff != is_admin:
            user.is_staff = is_admin
            user.save(update_fields=['is_staff'])


class Migration(migrations.Migration):

    dependencies = [
        ('agenda', '0003_actetipus_acte_aforament_acte_fi_acte_punt_trobada_and_more'),
        ('usuaris', '0002_usuari_tipus'),
    ]

    operations = [
        migrations.AlterField(
            model_name='usuari',
            name='rol',
            field=models.CharField(
                choices=[
                    ('ADMINISTRACIO', 'Administració'),
                    ('COORDINACIO', 'Coordinació'),
                    ('PARTICIPANT', 'Participant'),
                ],
                default='PARTICIPANT',
                max_length=20,
            ),
        ),
        migrations.RunPython(normalize_roles_groups_and_segments, migrations.RunPython.noop),
    ]
