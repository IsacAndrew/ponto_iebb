import React,{useState,useEffect,useRef} from 'react';
import {createRoot} from 'react-dom/client';
import {Clock3,History,Users,FileSpreadsheet,ClipboardCheck,LifeBuoy,UserRound,LogOut,Menu,ShieldCheck,Check,MapPin,ArrowRight,Settings,Search} from 'lucide-react';
import {api,Field,Password,Button,Modal,Notice,dateNow,hours} from './ui';
import {People} from './people';
import {Records,Requests,Reports,Support,Profile,Chat} from './pages';
import './style.css';

function App(){
 const [me,setMe]=useState(null),[loading,setLoading]=useState(true),[page,setPage]=useState('Ponto'),[error,setError]=useState(''),[toast,setToast]=useState(''),[busy,setBusy]=useState(false),[takeover,setTakeover]=useState(null),[nav,setNav]=useState(false),[chat,setChat]=useState(false);
 const timer=useRef();
 const notify=text=>{setToast(text);clearTimeout(timer.current);timer.current=setTimeout(()=>setToast(''),6500);};
 const run=async fn=>{setBusy(true);setError('');try{return await fn();}catch(e){setError(e.message);window.dispatchEvent(new CustomEvent('ponto-error',{detail:e.message}));if(e.status===401)setMe(null);return null;}finally{setBusy(false);}};
 const refresh=async()=>{try{const r=await api('/me');setMe(r.user);setTakeover(r.takeover);}catch(e){if(e.status===401)setMe(null);}finally{setLoading(false);}};
 useEffect(()=>{refresh();},[]);
 useEffect(()=>{if(!me)return;const t=setInterval(refresh,1000);return()=>clearInterval(t);},[me?.id]);
 const ctx={me,run,busy,notify,refresh};
 const change=p=>{setPage(p);setError('');setNav(false);};
 if(loading)return <div className="login-shell">Carregando…</div>;
 if(!me)return <><Login onLogin={p=>{setMe(p);setPage(p.role==='Diretoria'?'Pessoas':'Ponto');}} run={run} busy={busy}/>{error&&<div className="toast error" role="alert">{error}<button onClick={()=>setError('')}>×</button></div>}</>;
 const admin=['Administração','Diretoria','Suporte'].includes(me.role);
 const links=[...(me.role!=='Diretoria'?[['Ponto',Clock3],['Meu ponto',History]]:[]),...(admin?[['Pessoas',Users],['Registros',Search],['Excel',FileSpreadsheet]]:[]),['Solicitações',ClipboardCheck],['Falar com Suporte',LifeBuoy],...(me.role==='Suporte'?[['Central do Suporte',ShieldCheck]]:[]),['Meu perfil',UserRound]];
 return <div className="app"><aside className={nav?'sidebar open':'sidebar'}><div className="brand"><Clock3 size={26}/><strong>Livro-Ponto</strong></div><nav>{links.map(([name,Icon])=><button key={name} className={page===name?'selected':''} onClick={()=>change(name)}><Icon size={20}/>{name}</button>)}</nav><div className="account"><span className="avatar">{me.name[0]}</span><div><strong>{me.name.split(' ')[0]}</strong><span>{me.role}</span></div><button className="icon" title="Sair" onClick={()=>run(async()=>{await api('/logout',{});setMe(null);})}><LogOut size={19}/></button></div></aside>{nav&&<button className="nav-shade" aria-label="Fechar menu" onClick={()=>setNav(false)}/>}
 <main><header className="page-head"><button className="mobile icon" aria-label="Abrir menu" onClick={()=>setNav(true)}><Menu/></button><h1>{page}</h1></header>{error&&<div className="inline-error" role="alert">{error}<button onClick={()=>setError('')}>×</button></div>}
 {page==='Ponto'&&<Punch {...ctx}/>}{page==='Pessoas'&&admin&&<People {...ctx}/>}{['Meu ponto','Registros'].includes(page)&&<Records {...ctx} administrative={page==='Registros'&&admin}/>}{page==='Solicitações'&&<Requests {...ctx} admin={admin}/>}{page==='Excel'&&admin&&<Reports {...ctx}/>}{page==='Central do Suporte'&&me.role==='Suporte'&&<Support {...ctx}/>}{page==='Meu perfil'&&<Profile {...ctx}/>}{page==='Falar com Suporte'&&<Chat {...ctx}/>}
 </main>{!chat&&page!=='Falar com Suporte'&&<button className="help" aria-label="Falar com Suporte" onClick={()=>setChat(true)}>?</button>}{chat&&<Modal title="Falar com Suporte" close={()=>setChat(false)}><Chat {...ctx}/></Modal>}
 {toast&&<div className="toast" role="status"><Check size={18}/>{toast}</div>}{takeover&&<Modal title="Novo acesso à sua conta" close={()=>{}}><p>Outro dispositivo está entrando. Cancele agora para continuar aqui.</p><Button className="primary" onClick={()=>run(async()=>{await api('/session/cancel',{});setTakeover(null);})}>Cancelar novo acesso</Button></Modal>}{me.temporary&&<ChangePassword {...ctx}/>}</div>;
}
function Login({onLogin,run,busy}){
 const [login,setLogin]=useState(''),[password,setPassword]=useState(''),[pending,setPending]=useState(null),[message,setMessage]=useState('');
 useEffect(()=>{if(!pending)return;let active=true;const t=setInterval(async()=>{try{const r=await api('/login/claim',{ticket:pending});if(active&&!r.pending){setPending(null);onLogin(r.user);}}catch(e){if(active){setPending(null);setMessage(e.message);}}},700);return()=>{active=false;clearInterval(t);};},[pending]);
 return <div className="login-shell"><form className="login-card" onSubmit={e=>{e.preventDefault();run(async()=>{const r=await api('/login',{login,password});if(r.pending)setPending(r.ticket);else onLogin(r.user);});}}><div className="login-mark"><Clock3 size={29}/></div><h1>Livro-Ponto</h1><Field label="Login" autoComplete="username" value={login} onChange={e=>setLogin(e.target.value)} required autoFocus/><Password value={password} autoComplete="current-password" onChange={e=>setPassword(e.target.value)} required/>{message&&<Notice>{message}</Notice>}{pending&&<Notice>Aguardando o outro dispositivo…</Notice>}<Button className="primary" busy={busy||!!pending} type="submit">Entrar <ArrowRight size={18}/></Button></form></div>;
}
function ChangePassword({run,busy,refresh}){
 const [current,setCurrent]=useState(''),[password,setPassword]=useState(''),[repeat,setRepeat]=useState('');
 return <Modal title="Crie sua senha definitiva" close={()=>{}}><form onSubmit={e=>{e.preventDefault();run(async()=>{if(password!==repeat)throw Error('As senhas não conferem.');await api('/password',{current,password});await refresh();});}}><Password label="Senha temporária" value={current} onChange={e=>setCurrent(e.target.value)} required/><Password label="Nova senha" value={password} minLength={8} autoComplete="new-password" onChange={e=>setPassword(e.target.value)} required/><Password label="Repita a nova senha" value={repeat} minLength={8} autoComplete="new-password" onChange={e=>setRepeat(e.target.value)} required/><p className="muted">Use pelo menos 8 caracteres.</p><Button className="primary" busy={busy}>Salvar senha</Button></form></Modal>;
}
function Punch({run,busy,notify}){
 const [day,setDay]=useState(null),[clock,setClock]=useState(new Date()),[geo,setGeo]=useState(''),[question,setQuestion]=useState(null),[success,setSuccess]=useState(false),[test,setTest]=useState(false);
 const offset=useRef(0),draft=useRef(null),lock=useRef(false);
 const load=async()=>{const d=await api('/punch/today');setDay(d);offset.current=new Date(d.now).getTime()-Date.now();};
 useEffect(()=>{run(load);const t=setInterval(()=>{setClock(new Date(Date.now()+offset.current));},1000);const reload=setInterval(()=>load().catch(()=>{}),15000);return()=>{clearInterval(t);clearInterval(reload);};},[]);
 const send=async additions=>{
   if(lock.current)return;lock.current=true;
   try{await run(async()=>{
    const payload={...(draft.current||{key:crypto.randomUUID()}),...additions,test};draft.current=payload;
    if(!test&&!payload.lat){try{const position=await new Promise((ok,no)=>navigator.geolocation?navigator.geolocation.getCurrentPosition(ok,no,{enableHighAccuracy:true,timeout:15000,maximumAge:0}):no(Error()));payload.lat=position.coords.latitude;payload.lon=position.coords.longitude;payload.accuracy=position.coords.accuracy;}catch{setGeo('Permita a localização nas configurações deste site e tente novamente.');return;}}
    let r;try{r=await api('/punch',payload);}catch(e){if(e.status===422){setGeo(e.message);return;}throw e;}
    if(r.question){setQuestion(r);return;}
    setDay(r.day);setQuestion(null);setGeo('');draft.current=null;setSuccess(true);notify(r.message);setTimeout(()=>setSuccess(false),2400);
   });}finally{lock.current=false;}
 };
 const expected=day?.periods.flat()||[],index=day?.punches.length||0,done=day&&index>=expected.length;
 return <div className="punch-area"><section className="punch-card"><div className="clock-icon"><Clock3 size={29}/></div><div className="clock">{clock.toLocaleTimeString('pt-BR',{timeZone:'America/Sao_Paulo',hour:'2-digit',minute:'2-digit'})}<span>{clock.toLocaleTimeString('pt-BR',{timeZone:'America/Sao_Paulo',second:'2-digit'})}</span></div><div className="next">{day?(done?(index%2?'Saída de hora extra':'Jornada concluída'):`${index%2?'Saída':'Entrada'} · ${expected[index]}`):'Carregando…'}</div><Button className={`primary punch-button ${success?'success':''}`} busy={busy} disabled={!day||done&&index%2===0} onClick={()=>{draft.current=null;send({});}}>{success?<><Check/>Ponto registrado</>:done&&index%2===0?'Até o próximo dia':'Registrar ponto'}</Button>{done&&index%2===0&&<button className="text-button extra-action" onClick={()=>{draft.current=null;setQuestion({question:'overtime',message:'Você está fazendo hora extra?'});}}>Registrar hora extra</button>}{day?.test_bypass&&<label className="check test-toggle"><input type="checkbox" checked={test} onChange={e=>setTest(e.target.checked)}/>Teste sem localização</label>}</section>{geo&&<section className="location-card"><MapPin/><div><h2>Verificar localização</h2><p>{geo}</p><Button busy={busy} className="secondary" onClick={()=>{draft.current=null;send({});}}>Tentar novamente</Button></div></section>}{question&&<Modal title={question.message} close={()=>{setQuestion(null);draft.current=null;}}><div className="actions"><Button className="secondary" onClick={()=>{const q=question;setQuestion(null);if(q.question==='forgot')send({forgot:'no'});else draft.current=null;}}>Não</Button><Button className="primary" busy={busy} onClick={()=>{const q=question;setQuestion(null);send(q.question==='forgot'?{forgot:'yes'}:{overtime:true});}}>Sim</Button></div></Modal>}</div>;
}
createRoot(document.getElementById('root')).render(<App/>);
