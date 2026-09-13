import React, { useState } from "react";
import {
  ArrowRight,
  Clock3,
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
      <section className="auth-form-side">
        <div className="auth-form-wrap">
          <div className="login-mark">
            {recovery ? <KeyRound /> : <Clock3 />}
          </div>
          <h2>{recovery ? "Recuperar acesso" : "Entrar"}</h2>
          {recovery && (
            <p className="muted">
              Informe seu login para recuperar o acesso por e-mail.
            </p>
          )}
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
        </div>
      </section>
    </main>
  );
}

export function AccessChoice({ me, run, busy, error, choose, logout }) {
  return (
    <main className="access-shell">
      <section className="access-choice">
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
