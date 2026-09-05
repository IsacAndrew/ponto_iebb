import hashlib, hmac, secrets, time, os
from fastapi import Request
from .db import Person, Setting
from .rules import fail

def digest(value): return hashlib.sha256(value.encode()).hexdigest()
def password_hash(value):
    salt=secrets.token_hex(16)
    return salt+':'+hashlib.pbkdf2_hmac('sha256',value.encode(),salt.encode(),310000).hex()
def verify(value, stored):
    salt, hashed=stored.split(':')
    return hmac.compare_digest(hashlib.pbkdf2_hmac('sha256',value.encode(),salt.encode(),310000).hex(),hashed)
def cookie(response, token):
    response.set_cookie('ponto_session',token,httponly=True,samesite='strict',secure=bool(os.getenv('RENDER')),max_age=43200,path='/')
FULL_ACCESS = ('Suporte', 'Diretoria')
def current(db, request: Request, allow_temporary=False):
    token=request.cookies.get('ponto_session','')
    if not token or ':' not in token: fail('Entre novamente.',401)
    try: person=db.get(Person,int(token.split(':')[0]))
    except ValueError: fail('Entre novamente.',401)
    if not person or not person.active: fail('Entre novamente.',401)
    state=person.session or {}
    if not hmac.compare_digest(state.get('token',''),digest(token)) or state.get('expires',0)<time.time(): fail('Entre novamente.',401)
    if person.temporary and not allow_temporary: fail('Crie sua senha definitiva.',403)
    return person
def require(person, roles):
    if person.role not in roles: fail('Você não tem acesso a esta ação.',403)
def confirm(person, password):
    if not verify(password,person.password): fail('Senha incorreta.',403)
def public(person):
    return dict(id=person.id,name=person.name,login=person.login,role=person.role,active=person.active,hired=person.hired,terminated=person.terminated,details=person.details,temporary=person.temporary)
