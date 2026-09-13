import React, {
  useState,
  useEffect,
  useRef,
  useCallback,
  lazy,
  Suspense,
} from "react";
import {
  Clock3,
  Fingerprint,
  History,
  Users,
  Search,
  FileSpreadsheet,
  ClipboardCheck,
  LifeBuoy,
  ShieldCheck,
  Settings,
  UserRound,
  Table2,
  LogOut,
  Menu,
  X,
  ArrowRight,
  WifiOff,
} from "lucide-react";
import { api, SuccessToast } from "./ui";
import { Login, FirstPassword, AccessChoice } from "./components/auth";
import { Punch } from "./components/punch";
const loadPage = (path, name) =>
  lazy(() => path().then((m) => ({ default: m[name] })));
const People = loadPage(() => import("./people"), "People");
const Records = loadPage(() => import("./pages/records"), "Records");
const Management = loadPage(() => import("./pages/management"), "Management");
const Requests = loadPage(() => import("./pages/requests"), "Requests");
const Reports = loadPage(() => import("./pages/reports"), "Reports");
const Profile = loadPage(() => import("./pages/profile"), "Profile");
const Chat = loadPage(() => import("./pages/chat"), "Chat");
const Support = loadPage(() => import("./pages/support"), "Support");
const SettingsPage = loadPage(() => import("./pages/settings"), "SettingsPage");
const MySchedule = loadPage(() => import("./my-schedule"), "MySchedule");
const titles = {
  "Meus Registros": "Meu histórico",
  "Meu Perfil": "Meu perfil",
  "Meus Horários": "Meus horários",
  Usuários: "Pessoas",
  Marcações: "Gestão de ponto",
  Excel: "Relatórios",
  Solicitações: "Solicitações",
  Atendimentos: "Atendimentos",
  "Central de Suporte": "Ocorrências",
  Configurações: "Configurações",
  "Falar com Suporte": "Falar com o Suporte",
};
const subtitles = {
  Usuários: "Cadastros, perfis e jornadas da equipe.",
  Marcações: "Acompanhe a presença e os registros da escola.",
  Excel: "Os dados da sua equipe, prontos para consultar.",
  "Meus Registros": "Sua jornada registrada, dia após dia.",
  Solicitações: "Acompanhe os pedidos de ajuste e suas decisões.",
  "Central de Suporte": "Revise as situações que precisam de atenção.",
  Configurações: "Organize as preferências da escola.",
  "Meu Perfil": "Seus dados e sua jornada em um só lugar.",
};
export default function App() {
  const [me, setMe] = useState(null),
    [initial, setInitial] = useState(null),
    [loading, setLoading] = useState(true),
    [page, setPage] = useState("Ponto"),
    [error, setError] = useState(""),
    [toast, setToast] = useState(""),
    [busy, setBusy] = useState(false),
    [nav, setNav] = useState(false),
    [online, setOnline] = useState(navigator.onLine),
    [unread, setUnread] = useState(0);
  const generation = useRef(0),
    activeRuns = useRef(0),
    refreshing = useRef(false),
    timer = useRef();
  const notify = useCallback((text) => {
    setToast(text);
    clearTimeout(timer.current);
    timer.current = setTimeout(() => setToast(""), 6000);
  }, []);
  const run = useCallback(async (fn) => {
    generation.current++;
    activeRuns.current++;
    setBusy(true);
    setError("");
    try {
      return await fn();
    } catch (e) {
      setError(e.message);
      window.dispatchEvent(
        new CustomEvent("ponto-error", { detail: e.message }),
      );
      if (e.status === 401) {
        generation.current++;
        setMe(null);
        setInitial(null);
      }
      return null;
    } finally {
      activeRuns.current--;
      setBusy(activeRuns.current > 0);
    }
  }, []);
  const refresh = useCallback(async () => {
    if (refreshing.current) return;
    refreshing.current = true;
    const version = generation.current;
    try {
      const r = await api("/me");
      if (version === generation.current) {
        setMe(r.user);
        setInitial(r.punch);
      }
    } catch (e) {
      if (version === generation.current) {
        if (e.status === 401) {
          setMe(null);
          setInitial(null);
        } else setError(e.message);
      }
    } finally {
      refreshing.current = false;
      setLoading(false);
    }
  }, []);
  useEffect(() => {
    refresh();
    const update = () => setOnline(navigator.onLine);
    window.addEventListener("online", update);
    window.addEventListener("offline", update);
    return () => {
      clearTimeout(timer.current);
      window.removeEventListener("online", update);
      window.removeEventListener("offline", update);
    };
  }, []);
  useEffect(() => {
    if (!me) return;
    const update = () => {
      if (document.visibilityState === "visible" && activeRuns.current === 0)
        refresh();
    };
    const interval = setInterval(update, 30000);
    document.addEventListener("visibilitychange", update);
    return () => {
      clearInterval(interval);
      document.removeEventListener("visibilitychange", update);
    };
  }, [me?.id]);
  useEffect(() => {
    if (me?.role !== "Suporte" || me.temporary || me.access_required) {
      setUnread(0);
      return;
    }
    let active = true;
    const load = async () => {
      try {
        const r = await api("/tickets/unread");
        if (active) setUnread(r.count);
      } catch {}
    };
    load();
    const t = setInterval(load, 30000);
    return () => {
      active = false;
      clearInterval(t);
    };
  }, [me?.id, me?.role, me?.temporary, me?.access_required]);
  const choose = (r) => {
    generation.current++;
    setMe(r.user);
    setInitial(r.punch);
    setError("");
    setPage(r.user.role === "Diretoria" ? "Marcações" : "Ponto");
    const back = sessionStorage.getItem("ponto_qr_return");
    if (
      back &&
      !r.user.temporary &&
      !r.user.access_required &&
      /^\/q\/[A-Za-z0-9_-]+$/.test(back)
    ) {
      sessionStorage.removeItem("ponto_qr_return");
      location.assign(back);
    }
  };
  const logout = () =>
    run(async () => {
      await api("/logout", {});
      generation.current++;
      setMe(null);
      setInitial(null);
      setNav(false);
      setToast("");
      setUnread(0);
    });
  const change = (name) => {
    setPage(name);
    setError("");
    setNav(false);
    if (name === "Atendimentos")
      run(async () => {
        await api("/tickets/read", {});
        setUnread(0);
      });
    window.scrollTo({ top: 0 });
  };
  useEffect(() => {
    if (!nav) return;
    const old = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const escape = (e) => {
      if (e.key === "Escape") setNav(false);
    };
    document.addEventListener("keydown", escape);
    return () => {
      document.body.style.overflow = old;
      document.removeEventListener("keydown", escape);
    };
  }, [nav]);
  if (loading)
    return (
      <div className="access-shell">
        <div className="loading-state" role="status">
          <Clock3 className="pulse" />
          <p>Preparando sua jornada…</p>
        </div>
      </div>
    );
  if (!me) return <Login {...{ run, busy, error }} onLogin={choose} />;
  if (me.temporary)
    return (
      <FirstPassword
        {...{ run, busy, error, logout }}
        refresh={async () => {
          const r = await api("/me");
          choose(r);
        }}
      />
    );
  if (me.access_required)
    return <AccessChoice {...{ me, run, busy, error, choose, logout }} />;
  const admin = ["Administração", "Diretoria", "Suporte"].includes(me.role),
    full = ["Suporte", "Diretoria"].includes(me.role);
  const personal = [
    ...(me.role !== "Diretoria" ? [["Ponto", Fingerprint]] : []),
    ["Meus Registros", History],
    ...(me.role === "Professor" ? [["Meus Horários", Table2]] : []),
    ["Meu Perfil", UserRound],
    ["Solicitações", ClipboardCheck],
  ];
  const management = admin
    ? [
        ["Usuários", Users],
        ["Marcações", Search],
        ["Excel", FileSpreadsheet],
        ...(me.role === "Suporte"
          ? [
              ["Atendimentos", LifeBuoy],
              ["Central de Suporte", ShieldCheck],
            ]
          : []),
        ...(full ? [["Configurações", Settings]] : []),
      ]
    : [];
  const ctx = { me, run, busy, notify, refresh };
  let content;
  if (page === "Ponto" && me.role !== "Diretoria")
    content = <Punch {...ctx} initial={initial} onNavigate={change} />;
  else if (page === "Usuários" && admin) content = <People {...ctx} />;
  else if (page === "Marcações" && admin) content = <Management {...ctx} />;
  else if (page === "Excel" && admin) content = <Reports {...ctx} />;
  else if (page === "Solicitações")
    content = <Requests {...ctx} admin={full} />;
  else if (page === "Atendimentos" && me.role === "Suporte")
    content = <Chat {...ctx} management />;
  else if (page === "Central de Suporte" && me.role === "Suporte")
    content = <Support {...ctx} />;
  else if (page === "Configurações" && full)
    content = <SettingsPage {...ctx} />;
  else if (page === "Meu Perfil") content = <Profile {...ctx} />;
  else if (page === "Meus Horários" && me.role === "Professor")
    content = <MySchedule {...ctx} />;
  else if (page === "Falar com Suporte") content = <Chat {...ctx} />;
  else content = <Records {...ctx} />;
  return (
    <div className="app">
      <a className="skip-link" href="#main-content">
        Pular para o conteúdo
      </a>
      <aside
        className={nav ? "sidebar open" : "sidebar"}
        aria-label="Menu principal"
      >
        <a
          className="product-brand"
          href="/"
          onClick={(e) => {
            e.preventDefault();
            change(me.role === "Diretoria" ? "Marcações" : "Ponto");
          }}
        >
          <span className="brand-symbol">
            <Clock3 size={24} />
          </span>
          <span>
            ponto<span className="brand-dot">.</span>
            <small>IEBB · SUA JORNADA</small>
          </span>
        </a>
        <button
          className="mobile icon close-nav"
          aria-label="Fechar menu"
          onClick={() => setNav(false)}
        >
          <X />
        </button>
        <nav>
          <span className="nav-label">MEU ESPAÇO</span>
          {personal.map(([name, Icon]) => (
            <button
              key={name}
              aria-current={page === name ? "page" : undefined}
              className={page === name ? "selected" : ""}
              onClick={() => change(name)}
            >
              <Icon size={19} />
              <span>{titles[name] || name}</span>
            </button>
          ))}
          {management.length > 0 && (
            <span className="nav-label">GESTÃO DA ESCOLA</span>
          )}
          {management.map(([name, Icon]) => (
            <button
              key={name}
              aria-current={page === name ? "page" : undefined}
              className={page === name ? "selected" : ""}
              onClick={() => change(name)}
            >
              <Icon size={19} />
              <span>{titles[name] || name}</span>
              {name === "Atendimentos" && unread > 0 && (
                <b className="nav-badge">{unread}</b>
              )}
            </button>
          ))}
        </nav>
        {me.role !== "Suporte" && (
          <button
            className="sidebar-help"
            onClick={() => change("Falar com Suporte")}
          >
            <LifeBuoy size={21} />
            <div>
              <strong>Precisa de ajuda?</strong>
              <span>Fale com o Suporte</span>
            </div>
            <ArrowRight size={16} />
          </button>
        )}
        <div className="account">
          <span className="avatar">{me.name[0]}</span>
          <div>
            <strong>{me.name.split(" ")[0]}</strong>
            <span>{me.role}</span>
          </div>
          <button className="icon" aria-label="Sair da conta" onClick={logout}>
            <LogOut size={19} />
          </button>
        </div>
      </aside>
      {nav && (
        <button
          className="nav-shade"
          aria-label="Fechar navegação"
          onClick={() => setNav(false)}
        />
      )}
      <div className="workspace">
        <header className="workspace-header">
          <button
            className="mobile icon"
            aria-label="Abrir menu"
            aria-expanded={nav}
            onClick={() => setNav(true)}
          >
            <Menu />
          </button>
          <div className="breadcrumb">
            Meu espaço <span>/</span>
            <strong>{titles[page] || "Meu ponto"}</strong>
          </div>
          <div className="header-right">
            <span className="school-name">
              Instituto Educacional Batista Bíblico
            </span>
            <button
              className="header-avatar"
              onClick={() => change("Meu Perfil")}
              aria-label="Abrir meu perfil"
            >
              {me.name[0]}
            </button>
          </div>
        </header>
        <main id="main-content" tabIndex={-1}>
          {!online && (
            <div className="offline-banner" role="alert">
              <WifiOff size={18} />
              Você está sem conexão. Os pontos só são confirmados após o envio.
            </div>
          )}
          {error && (
            <div className="inline-error" role="alert">
              {error}
              <button aria-label="Fechar aviso" onClick={() => setError("")}>
                ×
              </button>
            </div>
          )}
          {page !== "Ponto" && (
            <div className="greeting page-heading">
              <span className="eyebrow">
                {admin ? "GESTÃO E ROTINA" : "MEU ESPAÇO"}
              </span>
              <h1>{titles[page] || page}</h1>
              <p>
                {subtitles[page] || "Tudo o que você precisa, em um só lugar."}
              </p>
            </div>
          )}
          <Suspense
            fallback={
              <div className="loading-state" role="status">
                Carregando…
              </div>
            }
          >
            <div key={me.id + ":" + me.role + ":" + page}>{content}</div>
          </Suspense>
          <footer className="workspace-footer">
            <span>Ponto IEBB</span>
            <span>Feito para a nossa rotina · v3.0</span>
          </footer>
        </main>
      </div>
      {toast && <SuccessToast message={toast} />}
    </div>
  );
}
