from datetime import date, timedelta
from math import radians, sin, cos, atan2, sqrt
from sqlalchemy import select
from fastapi import HTTPException
from .db import Schedule, Day, Setting, today

ROLES = ['Colaborador', 'Professor', 'Administração', 'Diretoria', 'Suporte']
ADMIN = ROLES[2:]
CLASSES = ['Jardim', 'Pré', '1º Ano A', '1º Ano B', '2º Ano A', '2º Ano B', '3º Ano A', '3º Ano B', '4º Ano A', '5º Ano A', '5º Ano B', '6º Ano A', '7º Ano A', '8º Ano A', '8º Ano B', '9º Ano A', '1ª Série', '2ª Série', '3ª Série']
def fail(message, code=400): raise HTTPException(code, message)
def minutes(value):
    h, m = map(int, value.split(':'))
    if not 0 <= h <= 23 or not 0 <= m <= 59: fail('Horário inválido.')
    return h * 60 + m
def valid_date(value):
    try: return date.fromisoformat(value).isoformat()
    except (ValueError, TypeError): fail('Data inválida.')
def validate_days(days):
    if not isinstance(days, dict) or set(days) - set(map(str, range(7))): fail('Jornada inválida.')
    for periods in days.values():
        previous = -1
        for pair in periods:
            if len(pair) != 2: fail('Informe entrada e saída.')
            try: start, end = map(minutes, pair)
            except (ValueError, TypeError): fail('Horário inválido.')
            if start >= end or start <= previous: fail('Os períodos devem estar em ordem, sem sobreposição.')
            previous = end
    return days
def schedule_for(db, person, day):
    rows = list(db.scalars(select(Schedule).where(Schedule.person_id == person.id, Schedule.effective <= day).order_by(Schedule.effective.desc(), Schedule.id.desc())))
    chosen = next((s for s in rows if s.specific and s.effective == day), None) or next((s for s in rows if not s.specific), None)
    return chosen.days.get(str(date.fromisoformat(day).weekday()), []) if chosen else []
def holiday(db, day):
    row = db.get(Setting, 'holiday:' + day)
    return row.data.get('name', '') if row else ''
def unlocked(db, day):
    row = db.get(Setting, 'month:' + day[:7])
    if row and row.data.get('closed'): fail('Mês fechado. Diretoria ou Suporte podem reabrir o período.', 409)
def get_day(db, person, day, create=False):
    row = db.get(Day, f'{person.id}:{day}')
    if not row and create:
        row = Day(key=f'{person.id}:{day}', person_id=person.id, date=day, periods=schedule_for(db, person, day), punches=[], absent=False, overtime='')
        db.add(row)
        db.flush()
    return row
def summarize(db, person, day):
    row = get_day(db, person, day)
    periods = row.periods if row else schedule_for(db, person, day)
    punches = row.punches if row else []
    free = holiday(db, day)
    expected = [t for pair in periods for t in pair]
    planned = sum(minutes(b)-minutes(a) for a,b in periods) if not free else 0
    worked = sum(max(0, minutes(punches[i+1]['time'])-minutes(punches[i]['time'])) for i in range(0, len(punches)-1, 2))
    late = negative = extra = 0
    for i,p in enumerate(punches[:len(expected)]):
        diff = minutes(p['time'])-minutes(expected[i])
        if i % 2 == 0:
            late += max(0, diff-5)
            negative += max(0, diff-5)
        else:
            negative += max(0, -diff)
            extra += max(0, diff-5)
    for i in range(len(expected), len(punches)-1, 2):
        extra += max(0, minutes(punches[i+1]['time'])-minutes(punches[i]['time']))
    absent = bool(row and row.absent)
    complete = len(punches) >= len(expected) and len(punches) % 2 == 0
    if free:
        negative = late = 0
        extra = worked
    status = free or ('Falta registrada' if absent and not punches else 'Falta com comparecimento' if absent else 'Sem expediente' if not expected and not punches else 'Completo' if complete and punches else 'Ponto incompleto' if punches else 'Sem marcações')
    if absent and not punches and not free: negative = planned
    balance = extra-negative if complete or absent or free else None
    return dict(person_id=person.id, name=person.name, role=person.role, date=day, periods=periods, punches=punches, planned=planned, worked=worked, extra=extra, negative=negative, late=late, balance=balance, absent=absent, status=status, holiday=free, overtime=row.overtime if row else '', expected=len(expected), terminated=person.terminated)
def distance(lat, lon, target_lat, target_lon):
    a,b = radians(lat),radians(target_lat)
    v=sin((b-a)/2)**2+cos(a)*cos(b)*sin(radians(target_lon-lon)/2)**2
    return 6371000*2*atan2(sqrt(v),sqrt(max(0,1-v)))
