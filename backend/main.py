import os, time, secrets, json, math, base64, logging, traceback
from datetime import date, timedelta
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response, Body
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from .db import ROOT, init, transaction, reading, Person, Schedule, Day, Item, Setting, Audit, audit, now, today
from .rules import ROLES, ADMIN, CLASSES, fail, minutes, valid_date, validate_days, schedule_for, holiday, unlocked, get_day, summarize, distance, suspect_missing
from .security import password_hash, verify, digest, cookie, current, require, confirm, public, FULL_ACCESS

@asynccontextmanager
async def lifespan(app):
    init()
    with transaction() as db:
        if not db.scalar(select(Person.id).limit(1)):
            login=os.getenv('BOOTSTRAP_LOGIN','suporte')
            if os.getenv('RENDER') and not os.getenv('BOOTSTRAP_PASSWORD'): raise RuntimeError('Defina BOOTSTRAP_PASSWORD no primeiro deploy.')
            db.add(Person(name='Isac',login=login,password=password_hash(os.getenv('BOOTSTRAP_PASSWORD','102030')),role='Suporte',hired=today(),details={},session={}))
        if not db.get(Setting,'geo'):
            db.add(Setting(key='geo',data={'lat':-23.67637077,'lon':-46.76243126,'verified':False,'accuracy':100}))
    yield

app=FastAPI(title='Livro-Ponto',lifespan=lifespan)
@app.middleware('http')
async def protection(request, call_next):
    if request.method not in ('GET','HEAD','OPTIONS') and request.headers.get('x-ponto') != '1':
        return JSONResponse({'detail':'Requisição não autorizada.'},status_code=403)
    request_id=secrets.token_hex(6)
    try:
        response=await call_next(request)
    except Exception as exc:
        original=getattr(exc,'orig',exc)
        frames=' > '.join(f'{Path(f.filename).name}:{f.lineno}:{f.name}' for f in traceback.extract_tb(exc.__traceback__))
        logging.getLogger('ponto').error('request=%s method=%s path=%s error=%s sqlstate=%s frames=%s',request_id,request.method,request.url.path,type(original).__name__,getattr(original,'sqlstate',None),frames)
        status=503 if isinstance(exc,SQLAlchemyError) else 500
        response=JSONResponse({'detail':'Não foi possível salvar agora. Tente novamente.' if request.method!='GET' else 'Não foi possível carregar agora. Tente novamente.','reference':request_id},status_code=status)
    response.headers['X-Request-ID']=request_id
    response.headers['X-Content-Type-Options']='nosniff'
    response.headers['X-Frame-Options']='DENY'
    response.headers['Referrer-Policy']='same-origin'
    response.headers['Content-Security-Policy']="default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
    if request.url.path.startswith('/api'): response.headers['Cache-Control']='no-store'
    return response

@app.api_route('/health',methods=['GET','HEAD'])
def health(): return {'status':'ok'}
@app.post('/api/login')
def login(request: Request, response: Response, data: dict=Body(...)):
    result=None
    with transaction() as db:
        name=str(data.get('login','')).strip().lower()
        rate=db.get(Setting,'attempt:'+digest(name))
        if not rate: rate=Setting(key='attempt:'+digest(name),data={}); db.add(rate)
        attempts=dict(rate.data)
        if attempts.get('until',0)>time.time(): return JSONResponse({'detail':'Muitas tentativas. Aguarde um minuto.'},status_code=429)
        person=db.scalar(select(Person).where(Person.login==name,Person.active==True))
        if not person or not verify(str(data.get('password','')),person.password):
            n=attempts.get('count',0)+1
            rate.data={'count':n if n<5 else 0,'until':time.time()+60 if n>=5 else 0}
            result=JSONResponse({'detail':'Login ou senha incorretos.'},status_code=401)
        else:
            rate.data={}
            state=person.session or {}
            previous=request.cookies.get('ponto_session','')
            same=previous and digest(previous)==state.get('token') and state.get('expires',0)>time.time()
            token=previous if same else f'{person.id}:'+secrets.token_urlsafe(32)
            person.session={'token':digest(token),'expires':time.time()+43200}
            cookie(response,token)
            result={'user':public(person)}
    return result
@app.get('/api/me')
def me(request: Request):
    with reading() as db:
        person=current(db,request,True)
        return {'user':public(person),'now':now().isoformat(),'test_bypass':bypass(person)}
@app.post('/api/logout')
def logout(request: Request,response: Response):
    with transaction() as db:
        person=current(db,request,True); person.session={}
    response.delete_cookie('ponto_session')
    return {'ok':True}
@app.post('/api/password')
def password(request: Request,data: dict=Body(...)):
    with transaction() as db:
        person=current(db,request,True); confirm(person,data.get('current',''))
        value=str(data.get('password',''))
        if len(value)<8 or len(value)>128 or value=='102030': fail('Use uma senha definitiva com 8 a 128 caracteres.')
        person.password=password_hash(value); person.temporary=False
        person.session={k:v for k,v in person.session.items() if k not in ('pending','deadline')}
        audit(db,person,'Senha alterada',person.id)
        return public(person)
@app.post('/api/profile/login')
def reveal(request: Request,data: dict=Body(...)):
    with transaction() as db:
        person=current(db,request); confirm(person,data.get('password',''))
        return {'login':person.login}

def bypass(person):
    return not os.getenv('RENDER') and os.getenv('SUPPORT_TEST_BYPASS','false').lower()=='true' and person.role=='Suporte' and person.login==os.getenv('BOOTSTRAP_LOGIN','suporte')
def occurrence(db,person,day,title,details=None):
    for existing in db.scalars(select(Item).where(Item.kind=='occurrence',Item.person_id==person.id,Item.date==day,Item.status=='Pendente')):
        if existing.data.get('title')==title: return
    db.add(Item(kind='occurrence',person_id=person.id,date=day,data={'title':title,**(details or {})}))
@app.get('/api/punch/today')
def punch_today(request: Request):
    with reading() as db:
        p=current(db,request)
        return {**summarize(db,p,today()),'now':now().isoformat(),'test_bypass':bypass(p),'geo_ready':bool(db.get(Setting,'geo') and db.get(Setting,'geo').data.get('verified'))}
@app.post('/api/punch')
def punch(request: Request,data: dict=Body(...)):
    with transaction() as db:
        p=current(db,request)
        if p.role=='Diretoria': fail('Este perfil não tem jornada obrigatória.')
        d=today(); unlocked(db,d)
        row=get_day(db,p,d,True)
        if not row.punches: row.periods=schedule_for(db,p,d)
        punches=list(row.punches)
        key=str(data.get('key',''))
        if not key or len(key)>100: fail('Atualize a página e tente novamente.')
        if any(x.get('key')==key for x in punches): return {'message':'Ponto registrado com sucesso','day':summarize(db,p,d)}
        stamp=now(); minute=stamp.hour*60+stamp.minute
        if punches and stamp.timestamp()-punches[-1]['epoch']<30: fail('Ponto já registrado. Aguarde antes de outra marcação.',409)
        expected=[x for pair in row.periods for x in pair]
        index=len(punches)
        extra=index>=len(expected) or bool(holiday(db,d))
        if extra and not data.get('overtime'): return {'question':'overtime','message':'Você está fazendo hora extra?'}
        if not extra and index%2==0 and minute<minutes(expected[index])-5:
            fail('Ponto liberado cinco minutos antes da entrada prevista.')
        unusual=not extra and suspect_missing(expected,index,minute)
        if unusual and data.get('forgot') not in ('yes','no'):
            return {'question':'forgot','message':'Você esqueceu a marcação anterior?'}
        test=bypass(p) and data.get('test') is True
        geo_row=db.get(Setting,'geo')
        geo=geo_row.data if geo_row else {}
        location={}
        if not test:
            if geo.get('verified') is not True: fail('A escola ainda precisa confirmar o local de registro. Procure a Diretoria ou o Suporte.',409)
            try: lat,lon,accuracy=[float(data[k]) for k in ('lat','lon','accuracy')]
            except (KeyError,ValueError,TypeError): fail('Permita a localização para registrar o ponto.',422)
            if not all(math.isfinite(x) for x in (lat,lon,accuracy)) or abs(lat)>90 or abs(lon)>180 or accuracy<0: fail('Localização inválida.',422)
            if accuracy>geo.get('accuracy',100): fail('Localização imprecisa. Aproxime-se de uma janela e tente novamente.',422)
            meters=distance(lat,lon,geo['lat'],geo['lon'])
            if meters>100: fail(f'Você está a {round(meters)} m da escola. Aproxime-se para registrar.',422)
            location={'lat':lat,'lon':lon,'accuracy':accuracy,'distance':round(meters,1)}
        punches.append({'time':stamp.strftime('%H:%M'),'at':stamp.isoformat(),'epoch':stamp.timestamp(),'key':key,'test':test,**location})
        row.punches=punches
        if unusual: occurrence(db,p,d,'Batida possivelmente esquecida' if data.get('forgot')=='yes' else 'Marcação fora do esperado',{'answer':data.get('forgot')})
        if extra: occurrence(db,p,d,'Batida adicional')
        if row.absent: occurrence(db,p,d,'Falta registrada com comparecimento')
        summary=summarize(db,p,d)
        if extra or summary['extra']>0:
            row.overtime='Pendente de validação'; occurrence(db,p,d,'Hora extra pendente')
        audit(db,p,'Registrar ponto',row.key,after={'time':punches[-1]['time'],'test':test})
        message='Ponto registrado com sucesso'
        if row.absent: message+='. Havia falta registrada. Procure o Suporte.'
        elif not extra and index%2==0 and minute-minutes(expected[index])>65: message+='. Atraso elevado: procure o Suporte.'
        return {'message':message,'day':summarize(db,p,d)}

def person_data(p): return {**public(p),'login':p.login}
@app.get('/api/people')
def people(request: Request):
    with reading() as db:
        require(current(db,request),ADMIN)
        return [person_data(p) for p in db.scalars(select(Person).order_by(Person.name))]
def clean_person(data):
    name=str(data.get('name','')).strip(); login=str(data.get('login','')).strip().lower(); role=data.get('role')
    if not name or len(name)>160 or not login or len(login)>100 or role not in ROLES: fail('Preencha nome, login e perfil válidos.')
    details={k:str(data.get('details',{}).get(k,''))[:250] for k in ('email','phone','birth')}
    details['phone']=''.join(c for c in details['phone'] if c.isdigit())
    return name,login,role,details
def editable(actor,target,role=None):
    if actor.role=='Administração' and ((target and target.role in FULL_ACCESS) or role in FULL_ACCESS): fail('Somente Diretoria ou Suporte gerenciam esse perfil.',403)
@app.post('/api/people')
def add_person(request: Request,data: dict=Body(...)):
    with transaction() as db:
        actor=current(db,request); require(actor,ADMIN)
        name,login,role,details=clean_person(data); editable(actor,None,role)
        if db.scalar(select(Person.id).where(Person.login==login)): fail('Este login já está em uso.')
        hired=valid_date(data.get('hired',today()))
        p=Person(name=name,login=login,role=role,details=details,hired=hired,password=password_hash('102030'),session={})
        db.add(p); db.flush(); audit(db,actor,'Cadastrar pessoa',p.id,after=person_data(p))
        return person_data(p)
@app.put('/api/people/{pid}')
def update_person(pid:int,request: Request,data: dict=Body(...)):
    with transaction() as db:
        actor=current(db,request); require(actor,ADMIN); p=db.get(Person,pid)
        if not p: fail('Pessoa não encontrada.',404)
        name,login,role,details=clean_person(data); editable(actor,p,role)
        if actor.id==pid and role!=p.role: fail('Você não pode alterar o próprio perfil de acesso.')
        if db.scalar(select(Person.id).where(Person.login==login,Person.id!=pid)): fail('Este login já está em uso.')
        before=person_data(p); details['lessons']=p.details.get('lessons',[])
        p.name,p.login,p.role,p.details=name,login,role,details
        if before['role']!=role: p.session={}
        audit(db,actor,'Alterar cadastro',pid,before,person_data(p),data.get('reason','Atualização cadastral'))
        return person_data(p)
@app.post('/api/people/{pid}/reset')
def reset(pid:int,request: Request):
    with transaction() as db:
        actor=current(db,request); require(actor,ADMIN); p=db.get(Person,pid)
        if not p: fail('Pessoa não encontrada.',404)
        editable(actor,p); p.password=password_hash('102030'); p.temporary=True; p.session={}
        audit(db,actor,'Redefinir senha temporária',pid); return {'ok':True}
@app.post('/api/people/{pid}/deactivate')
def deactivate(pid:int,request: Request,data: dict=Body(...)):
    with transaction() as db:
        actor=current(db,request); require(actor,ADMIN); p=db.get(Person,pid)
        if not p: fail('Pessoa não encontrada.',404)
        editable(actor,p)
        if p.id==actor.id: fail('Você não pode desativar sua própria conta.')
        d=valid_date(data.get('date',today())); unlocked(db,d)
        if d>today() or d<p.hired: fail('Informe uma data entre a admissão e hoje.')
        if db.scalar(select(Day.key).where(Day.person_id==pid,Day.date>d)): fail('Existem registros após essa data. Use a data do último dia trabalhado.')
        p.active=False; p.terminated=d; p.session={}
        audit(db,actor,'Inativar pessoa',pid,after={'date':d},reason=data.get('reason','Desligamento'))
        return {'ok':True}
@app.get('/api/people/{pid}/schedules')
def schedules(pid:int,request: Request):
    with reading() as db:
        p=current(db,request)
        if p.id!=pid: require(p,ADMIN)
        return [{'id':s.id,'effective':s.effective,'specific':s.specific,'days':s.days} for s in db.scalars(select(Schedule).where(Schedule.person_id==pid).order_by(Schedule.effective.desc(),Schedule.id.desc()))]
@app.post('/api/people/{pid}/schedules')
def add_schedule(pid:int,request: Request,data: dict=Body(...)):
    with transaction() as db:
        actor=current(db,request); require(actor,ADMIN); p=db.get(Person,pid)
        if not p: fail('Pessoa não encontrada.',404)
        d=valid_date(data.get('effective')); days=validate_days(data.get('days',{})); specific=bool(data.get('specific'))
        if d<today(): fail('Uma nova jornada não pode alterar o passado.')
        row=get_day(db,p,d)
        if d==today() and row and row.punches:
            d=(date.fromisoformat(d)+timedelta(days=1)).isoformat()
        unlocked(db,d)
        db.add(Schedule(person_id=pid,effective=d,days=days,specific=specific))
        if row and not row.punches and row.date==d: row.periods=days.get(str(date.fromisoformat(d).weekday()),[])
        audit(db,actor,'Alterar jornada',f'{pid}:{d}',after={'days':days,'specific':specific},reason=data.get('reason','Nova vigência'))
        return {'effective':d}
@app.put('/api/people/{pid}/lessons')
def lessons(pid:int,request: Request,data: dict=Body(...)):
    with transaction() as db:
        actor=current(db,request); require(actor,ADMIN); p=db.get(Person,pid)
        if not p or p.role!='Professor': fail('Selecione um professor.')
        rows=data.get('lessons',[])
        for row in rows:
            if row.get('class') not in CLASSES or str(row.get('day')) not in list(map(str,range(7))) or not row.get('subject') or minutes(row['start'])>=minutes(row['end']): fail('Confira os dados da aula.')
        before=p.details; p.details={**p.details,'lessons':rows}
        audit(db,actor,'Alterar grade pedagógica',pid,before,p.details); return {'ok':True}

@app.get('/api/records')
def records(request: Request,start:str,end:str,person_id:int|None=None):
    start=valid_date(start); end=valid_date(end)
    if end<start or (date.fromisoformat(end)-date.fromisoformat(start)).days>93: fail('Selecione até 93 dias.')
    with reading() as db:
        actor=current(db,request)
        if actor.role not in ADMIN: person_id=actor.id
        people=list(db.scalars(select(Person).where(Person.id==person_id))) if person_id else list(db.scalars(select(Person).order_by(Person.name)))
        result=[]; day=date.fromisoformat(start)
        while day.isoformat()<=end:
            d=day.isoformat()
            for p in people:
                if p.hired<=d and (not p.terminated or d<=p.terminated): result.append(summarize(db,p,d))
            day+=timedelta(days=1)
        return result
@app.get('/api/attendance')
def attendance(request: Request,day:str):
    valid_date(day)
    with reading() as db:
        require(current(db,request),ADMIN)
        rows=[summarize(db,p,day) for p in db.scalars(select(Person).order_by(Person.name)) if p.role!='Diretoria' and p.hired<=day and (not p.terminated or day<=p.terminated)]
        return sorted(rows,key=lambda r:(not bool(r['expected'] and not r['holiday']),r['name']))
@app.post('/api/absence')
def absence(request: Request,data:dict=Body(...)):
    with transaction() as db:
        actor=current(db,request); require(actor,ADMIN); d=valid_date(data.get('date')); unlocked(db,d)
        p=db.get(Person,data.get('person_id'))
        if not p: fail('Pessoa não encontrada.',404)
        row=get_day(db,p,d,True); before={'absent':row.absent}
        if data.get('absent') and (holiday(db,d) or not row.periods or p.role=='Diretoria'): fail('Não há expediente previsto nesta data.')
        row.absent=bool(data.get('absent'))
        audit(db,actor,'Registrar falta' if row.absent else 'Desmarcar falta',row.key,before,{'absent':row.absent})
        if row.absent and row.punches: occurrence(db,p,d,'Falta registrada com comparecimento')
        return {'ok':True}

def apply_correction(db,actor,p,d,times,reason):
    unlocked(db,d)
    if not reason.strip(): fail('Informe o motivo.')
    if d>today(): fail('Não é possível corrigir uma data futura.')
    if d<p.hired or p.terminated and d>p.terminated: fail('Data fora do vínculo da pessoa.')
    values=[minutes(t) for t in times]
    if values!=sorted(set(values)): fail('As marcações devem estar em ordem e sem horários repetidos.')
    row=get_day(db,p,d,True); before={'punches':row.punches}
    row.punches=[{'time':t,'at':d+'T'+t+':00-03:00','epoch':__import__('datetime').datetime.fromisoformat(d+'T'+t+':00-03:00').timestamp(),'key':secrets.token_hex(12),'corrected':True,'test':False} for t in times]
    audit(db,actor,'Corrigir ponto',row.key,before,{'punches':row.punches},reason)
    if summarize(db,p,d)['extra']>0:
        row.overtime='Pendente de validação'; occurrence(db,p,d,'Hora extra pendente')
    else: row.overtime=''
@app.post('/api/corrections')
def corrections(request:Request,data:dict=Body(...)):
    with transaction() as db:
        actor=current(db,request); require(actor,ADMIN); p=db.get(Person,data.get('person_id'))
        if not p: fail('Pessoa não encontrada.',404)
        apply_correction(db,actor,p,valid_date(data.get('date')),data.get('times',[]),str(data.get('reason','')))
        return {'ok':True}
@app.get('/api/requests')
def requests(request:Request):
    with reading() as db:
        actor=current(db,request)
        return [item_json(db,r) for r in db.scalars(select(Item).where(Item.kind=='request').order_by(Item.id.desc())) if actor.role in ADMIN or r.person_id==actor.id]
def item_json(db,r):
    p=db.get(Person,r.person_id)
    return dict(id=r.id,kind=r.kind,person_id=r.person_id,name=p.name if p else '',date=r.date,status=r.status,data=r.data)
@app.put('/api/profile')
def update_profile(request:Request,data:dict=Body(...)):
    with transaction() as db:
        actor=current(db,request); require(actor,FULL_ACCESS)
        before=public(actor)
        name=str(data.get('name',actor.name)).strip()
        if not name or len(name)>160: fail('Informe um nome válido.')
        details={**actor.details}
        for key in ('email','phone','birth'):
            if key in data:
                value=str(data[key]).strip()[:250]
                details[key]=''.join(c for c in value if c.isdigit()) if key=='phone' else value
        actor.name=name; actor.details=details
        audit(db,actor,'Editar próprio cadastro',actor.id,before,public(actor),'Atualização pelo titular')
        return public(actor)

@app.post('/api/requests')
def new_request(request:Request,data:dict=Body(...)):
    with transaction() as db:
        p=current(db,request)
        kind=data.get('type')
        if kind not in ('point','profile') or not str(data.get('reason','')).strip(): fail('Informe a alteração e o motivo.')
        if kind=='point':
            d=valid_date(data.get('date')); unlocked(db,d)
            for t in data.get('times',[]): minutes(t)
            before={'punches':summarize(db,p,d)['punches']}
        else:
            d=today()
            if data.get('field') not in ('name','email','phone','birth') or not str(data.get('value','')).strip(): fail('Informe o campo e o novo valor.')
            before={'value':p.name if data['field']=='name' else p.details.get(data['field'],'')}
        r=Item(kind='request',person_id=p.id,date=d,data={**data,'before':before}); db.add(r); db.flush()
        audit(db,p,'Solicitar alteração',f'{p.id}:{d}',after={'request':r.id},reason=data['reason'])
        return {'ok':True}
@app.post('/api/requests/{rid}/decide')
def decide(rid:int,request:Request,data:dict=Body(...)):
    with transaction() as db:
        actor=current(db,request); require(actor,ADMIN); r=db.get(Item,rid)
        if not r or r.kind!='request' or r.status!='Pendente': fail('Solicitação não está pendente.')
        p=db.get(Person,r.person_id); approved=data.get('approve') is True
        reason=str(data.get('reason','')).strip()
        if not reason: fail('Informe o motivo da decisão.')
        if approved:
            if r.data['type']=='point':
                actual=summarize(db,p,r.date)['punches']
                if [x['time'] for x in actual]!=[x['time'] for x in r.data['before']['punches']]: fail('O ponto mudou desde a solicitação. Revise os horários.')
                apply_correction(db,actor,p,r.date,r.data.get('times',[]),reason)
            else:
                field=r.data['field']; value=r.data['value']
                actual=p.name if field=='name' else p.details.get(field,'')
                if actual!=r.data['before']['value']: fail('O cadastro mudou desde a solicitação. Revise os dados.')
                if field=='name': p.name=value[:160]
                else: p.details={**p.details,field:value[:250]}
                audit(db,actor,'Aprovar alteração cadastral',p.id,{'value':actual},{'value':value},reason)
        r.status='Aprovada' if approved else 'Reprovada'
        r.data={**r.data,'decision_by':actor.name,'decision_at':now().isoformat(),'decision_reason':reason}
        audit(db,actor,'Decidir solicitação',f'{r.person_id}:{r.date}',after={'status':r.status,'request':rid},reason=reason)
        return {'ok':True}

@app.get('/api/support/occurrences')
def occurrences(request:Request):
    with transaction() as db:
        require(current(db,request),FULL_ACCESS)
        for row in db.scalars(select(Day).where(Day.date<today())):
            if len(row.punches)<len(row.periods)*2 and row.punches or len(row.punches)%2:
                occurrence(db,db.get(Person,row.person_id),row.date,'Ponto incompleto')
        db.flush()
        return [item_json(db,r) for r in db.scalars(select(Item).where(Item.kind=='occurrence').order_by(Item.id.desc()))]
@app.post('/api/support/occurrences/{rid}')
def resolve(rid:int,request:Request,data:dict=Body(...)):
    with transaction() as db:
        actor=current(db,request); require(actor,FULL_ACCESS); r=db.get(Item,rid)
        if not r or r.kind!='occurrence' or r.status!='Pendente': fail('Ocorrência não está pendente.')
        unlocked(db,r.date)
        reason=str(data.get('reason','')).strip()
        if not reason: fail('Informe o resultado da análise.')
        if r.data.get('title')=='Hora extra pendente':
            row=get_day(db,db.get(Person,r.person_id),r.date)
            row.overtime='Validada' if data.get('approve') else 'Não validada'
        r.status='Concluída'; r.data={**r.data,'resolution':reason,'by':actor.name}
        audit(db,actor,'Analisar ocorrência',f'{r.person_id}:{r.date}',after=r.data,reason=reason)
        return {'ok':True}
@app.get('/api/tickets')
def tickets(request:Request, management:bool=False):
    with reading() as db:
        actor=current(db,request)
        if management: require(actor,FULL_ACCESS)
        return [item_json(db,r) for r in db.scalars(select(Item).where(Item.kind=='ticket').order_by(Item.id.desc())) if (management or actor.role=='Suporte') or r.person_id==actor.id]
@app.post('/api/tickets')
def new_ticket(request:Request,data:dict=Body(...)):
    with transaction() as db:
        actor=current(db,request)
        if actor.role=='Suporte': fail('Selecione um chamado para responder.',403)
        message=str(data.get('message','')).strip()
        if not message or len(message)>4000: fail('Escreva uma mensagem com até 4000 caracteres.')
        row=db.scalar(select(Item).where(Item.kind=='ticket',Item.person_id==actor.id))
        if not row: row=Item(kind='ticket',person_id=actor.id,data={'messages':[]}); db.add(row)
        row.data={'messages':row.data['messages']+[{'name':actor.name,'support':actor.role in FULL_ACCESS and row.person_id!=actor.id,'text':message,'at':now().isoformat()}]}
        return {'ok':True}
@app.post('/api/tickets/{rid}/message')
def message(rid:int,request:Request,data:dict=Body(...)):
    with transaction() as db:
        actor=current(db,request); row=db.get(Item,rid)
        if not row or row.kind!='ticket' or actor.role not in FULL_ACCESS and row.person_id!=actor.id: fail('Chamado não encontrado.',404)
        value=str(data.get('message','')).strip()
        if not value or len(value)>4000: fail('Escreva uma mensagem com até 4000 caracteres.')
        row.data={'messages':row.data['messages']+[{'name':actor.name,'support':actor.role in FULL_ACCESS and row.person_id!=actor.id,'text':value,'at':now().isoformat()}]}
        return {'ok':True}
@app.delete('/api/tickets/{rid}')
def close_ticket(rid:int,request:Request):
    with transaction() as db:
        require(current(db,request),FULL_ACCESS); row=db.get(Item,rid)
        if not row or row.kind!='ticket': fail('Chamado não encontrado.',404)
        db.delete(row)
        return {'ok':True}

@app.get('/api/calendar')
def calendar(request:Request):
    with reading() as db:
        require(current(db,request),ADMIN)
        return [{'date':r.key[8:],**r.data} for r in db.scalars(select(Setting).where(Setting.key.like('holiday:%')).order_by(Setting.key))]
@app.post('/api/calendar')
def save_holiday(request:Request,data:dict=Body(...)):
    with transaction() as db:
        actor=current(db,request); require(actor,ADMIN); d=valid_date(data.get('date')); unlocked(db,d)
        name=str(data.get('name','')).strip(); row=db.get(Setting,'holiday:'+d); before=row.data if row else {}
        if not name:
            if row: db.delete(row)
        elif row: row.data={'name':name[:120]}
        else: db.add(Setting(key='holiday:'+d,data={'name':name[:120]}))
        audit(db,actor,'Alterar calendário',d,before,{'name':name}); return {'ok':True}
@app.get('/api/support/settings')
def settings(request:Request):
    with reading() as db:
        require(current(db,request),FULL_ACCESS)
        row=db.get(Setting,'geo')
        return row.data if row else {'lat':-23.67637077,'lon':-46.76243126,'accuracy':100,'verified':False}
@app.put('/api/support/settings')
def save_settings(request:Request,data:dict=Body(...)):
    with transaction() as db:
        actor=current(db,request); require(actor,FULL_ACCESS); confirm(actor,data.get('password',''))
        try: lat,lon,accuracy=float(data['lat']),float(data['lon']),float(data['accuracy'])
        except (KeyError,ValueError,TypeError): fail('Confira as coordenadas e a precisão.')
        if not all(math.isfinite(v) for v in [lat,lon,accuracy]) or not -90<=lat<=90 or not -180<=lon<=180 or not 1<=accuracy<=100: fail('Confira as coordenadas e a precisão máxima (1 a 100 m).')
        row=db.get(Setting,'geo')
        if not row: row=Setting(key='geo',data={}); db.add(row)
        before=row.data
        row.data={'lat':lat,'lon':lon,'accuracy':accuracy,'verified':data.get('verified',before.get('verified',False)) is True}
        audit(db,actor,'Configurar localização','geo',before,row.data,'Confirmação do Suporte')
        return row.data
@app.get('/api/month/{month}')
def month_status(month:str,request:Request):
    valid_date(month+'-01')
    with reading() as db:
        require(current(db,request),ADMIN); row=db.get(Setting,'month:'+month)
        return row.data if row else {'closed':False,'version':0}
@app.post('/api/month/{month}/export')
def export(month:str,request:Request,data:dict=Body(...)):
    valid_date(month+'-01')
    from .excel import export_month
    with transaction() as db:
        actor=current(db,request); require(actor,ADMIN); row=db.get(Setting,'month:'+month)
        if not row: row=Setting(key='month:'+month,data={'closed':False,'version':0}); db.add(row)
        if not row.data.get('closed'):
            if month>today()[:7]: fail('Não é possível fechar um mês futuro.')
            confirm(actor,data.get('password',''))
            before=row.data
            row.data={'closed':True,'version':before.get('version',0)+1,'by':actor.name,'at':now().isoformat()}
            audit(db,actor,'Fechar mês',month,before,row.data)
        db.flush()
        key=f'export:{month}:{row.data["version"]}'
        snapshot=db.get(Setting,key)
        if snapshot:
            binary=base64.b64decode(snapshot.data['xlsx'])
        else:
            binary=export_month(db,month,row.data)
            db.add(Setting(key=key,data={'xlsx':base64.b64encode(binary).decode()}))
    return Response(binary,media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',headers={'Content-Disposition':f'attachment; filename="Ponto_{month}.xlsx"'})
@app.post('/api/month/{month}/reopen')
def reopen(month:str,request:Request,data:dict=Body(...)):
    valid_date(month+'-01')
    with transaction() as db:
        actor=current(db,request); require(actor,['Diretoria','Suporte']); confirm(actor,data.get('password',''))
        row=db.get(Setting,'month:'+month)
        if not row or not row.data.get('closed'): fail('O mês já está aberto.')
        reason=str(data.get('reason','')).strip()
        if not reason: fail('Informe o motivo da reabertura.')
        before=row.data; row.data={**before,'closed':False,'reopened_by':actor.name,'reopened_at':now().isoformat()}
        audit(db,actor,'Reabrir mês',month,before,row.data,reason); return row.data
@app.get('/api/audit')
def audit_list(request:Request,month:str):
    valid_date(month+'-01')
    with reading() as db:
        require(current(db,request),ADMIN)
        return [{'id':a.id,'at':a.at,'actor':a.actor,'action':a.action,'target':a.target,'before':a.before,'after':a.after,'reason':a.reason} for a in db.scalars(select(Audit).order_by(Audit.id.desc())) if month in a.target or a.at.startswith(month)]

dist=ROOT/'frontend'/'dist'
if dist.exists():
    app.mount('/assets',StaticFiles(directory=dist/'assets'),name='assets')
    @app.api_route('/{path:path}',methods=['GET','HEAD'])
    def frontend(path:str):
        if path.startswith('api/'): fail('Recurso não encontrado.',404)
        return FileResponse(dist/'index.html')
