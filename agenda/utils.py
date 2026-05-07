import calendar
from datetime import timedelta


def build_calendar_data(actes, anchor_date, today):
    month_start = anchor_date.replace(day=1)
    _, days_in_month = calendar.monthrange(month_start.year, month_start.month)
    month_end = month_start.replace(day=days_in_month)
    first_weekday = month_start.weekday()
    calendar_start = month_start - timedelta(days=first_weekday)
    calendar_end = month_end + timedelta(days=(6 - month_end.weekday()))

    events_by_day = {}
    for acte in actes:
        events_by_day.setdefault(acte.inici.date(), []).append(acte)

    calendar_cells = []
    cursor = calendar_start
    while cursor <= calendar_end:
        day_events = events_by_day.get(cursor, [])
        calendar_cells.append(
            {
                'date': cursor,
                'in_month': cursor.month == anchor_date.month,
                'is_today': cursor == today,
                'events': sorted(day_events, key=lambda event: event.inici),
            }
        )
        cursor += timedelta(days=1)

    return {
        'month_start': month_start,
        'month_end': month_end,
        'month_label': month_start.strftime('%B %Y'),
        'weeks': [calendar_cells[i:i + 7] for i in range(0, len(calendar_cells), 7)],
        'weekday_labels': ['Dl', 'Dt', 'Dc', 'Dj', 'Dv', 'Ds', 'Dg'],
        'prev_month': (month_start - timedelta(days=1)).replace(day=1),
        'next_month': (month_end + timedelta(days=1)).replace(day=1),
    }
