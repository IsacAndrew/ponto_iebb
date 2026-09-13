import React, { useState } from "react";
import {
  ArrowRight,
  Clock3,
  ShieldCheck,
  CalendarCheck2,
  KeyRound,
  ArrowLeft,
  UserRound,
} from "lucide-react";
import { api, Field, Password, Button, Notice } from "../ui";

export function Login({ onLogin, run, busy, error }) {
  const [login, setLogin] = useState("");
  const [password, setPassword] = useState("");
  const [recovery, setRecovery] = useState(false);
  const [message, setMessage] = useState("");
  return (
    <main className="auth-layout">
      <section className="auth-story" aria-label="Ponto IEBB">
        <a href="/" className="product-brand">
          <span className="brand-symbol">
            <Clock3 size={23} />
          </span>
          <span>
            ponto<span className="brand-dot">.</span>
            <small>INSTITUTO EDUCACIONAL BATISTA BÍBLICO</small>
          </span>
        </a>
        <div className="auth-story-content">
          <span className="eyebrow">MAIS TEMPO PARA O QUE IMPORTA</span>
          <h1>
            Sua jornada.
            <br />
            Tudo em
            <br />
            <em>seu tempo.</em>
          </h1>
          <p>
            Um jeito simples de registrar o ponto e acompanhar sua rotina na
            escola.
          </p>
          <div className="story-features">
            <span>
              <CalendarCheck2 size={18} /> Sua jornada organizada
            </span>
            <span>
              <ShieldCheck size={18} /> Seus registros em um só lugar
            </span>
          </div>
        </div>
        <div className="auth-footer">
          IEBB <span>Uma rotina mais conectada.</span>
        </div>
        <div className="orbit orbit-one" />
        <div className="orbit orbit-two" />
      </section>
      <section className="auth-form-side">
        <div className="auth-form-wrap">
          <span className="auth-tag">PORTAL DO COLABORADOR</span>
          <div className="login-mark">
            {recovery ? <KeyRound /> : <Clock3 />}
          </div>
          <h2>{recovery ? "Recuperar acesso" : "Bom ter você aqui."}</h2>
          <p className="muted">
            {recovery
              ? "Informe seu login para receber uma credencial por e-mail."
              : "Entre na sua conta para acompanhar sua jornada."}
          </p>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              run(async () => {
                if (recovery) {
                  const r = await api("/recover", { login });
                  setMessage(r.message);
                } else {
                  const r = await api("/login", { login, password });
                  onLogin(r);
                }
              });
            }}
          >
            {error && (
              <div className="inline-error" role="alert">
                {error}
              </div>
            )}
            {message && <Notice>{message}</Notice>}
            <Field
              label="Seu login"
              autoComplete="username"
              placeholder="Digite seu login"
              value={login}
              onChange={(e) => setLogin(e.target.value)}
              required
              maxLength={100}
            />
            {!recovery && (
              <Password
                label="Sua senha"
                autoComplete="current-password"
                placeholder="Digite sua senha"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                maxLength={128}
              />
            )}
            <Button type="submit" className="primary auth-submit" busy={busy}>
              {recovery ? "Enviar instruções" : "Entrar na minha conta"}
              <ArrowRight size={18} />
            </Button>
            <button
              className="text-button forgot"
              type="button"
              onClick={() => {
                setRecovery(!recovery);
                setMessage("");
              }}
            >
              {recovery ? (
                <>
                  <ArrowLeft size={16} />
                  Voltar para o login
                </>
              ) : (
                "Esqueci minha senha"
              )}
            </button>
          </form>
          <p className="auth-note">
            <ShieldCheck size={16} />
            Acesso exclusivo para a equipe IEBB.
          </p>
        </div>
        <footer>
          Ponto IEBB <span>Versão 3.0</span>
        </footer>
      </section>
    </main>
  );
}

export function FirstPassword({ run, busy, error, refresh, logout }) {
  const [password, setPassword] = useState(""),
    [repeat, setRepeat] = useState("");
  return (
    <main className="access-shell">
      <section className="login-card">
        <div className="login-mark">
          <KeyRound />
        </div>
        <span className="eyebrow">PRIMEIRO ACESSO</span>
        <h1>Uma senha só sua.</h1>
        <p className="muted">
          Crie uma senha com pelo menos 8 caracteres para liberar seu acesso.
        </p>
        {error && (
          <div className="inline-error" role="alert">
            {error}
          </div>
        )}
        <form
          onSubmit={(e) => {
            e.preventDefault();
            run(async () => {
              if (password !== repeat)
                throw new Error("As senhas não conferem.");
              await api("/password", { password });
              await refresh();
            });
          }}
        >
          <Password
            label="Nova senha"
            minLength={8}
            maxLength={128}
            autoComplete="new-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
          <Password
            label="Confirmar nova senha"
            minLength={8}
            maxLength={128}
            autoComplete="new-password"
            value={repeat}
            onChange={(e) => setRepeat(e.target.value)}
            required
          />
          <Button className="primary auth-submit" busy={busy}>
            Salvar e continuar
            <ArrowRight size={18} />
          </Button>
        </form>
        <button className="text-button" onClick={logout}>
          Sair da conta
        </button>
      </section>
    </main>
  );
}
export function AccessChoice({ me, run, busy, error, choose, logout }) {
  return (
    <main className="access-shell">
      <section className="access-choice">
        <span className="eyebrow">BEM-VINDO, {me.name.split(" ")[0]}</span>
        <h1>Como você vai acessar?</h1>
        <p className="muted">Escolha o perfil para esta sessão.</p>
        {error && (
          <div className="inline-error" role="alert">
            {error}
          </div>
        )}
        <div className="access-options">
          {me.roles.map((role) => (
            <button
              key={role}
              disabled={busy}
              onClick={() =>
                run(async () => choose(await api("/access", { role })))
              }
            >
              <UserRound />
              <strong>{role}</strong>
              <ArrowRight size={18} />
            </button>
          ))}
        </div>
        <button className="text-button" onClick={logout}>
          Sair da conta
        </button>
      </section>
    </main>
  );
}
