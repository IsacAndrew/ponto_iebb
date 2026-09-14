import React, { useState, useEffect } from "react";
import { Moon, Sun } from "lucide-react";

import {
  api,
  Field,
  Password,
  Button,
  Modal,
  dateNow,
  dateLabel,
  days,
  phoneFormat,
} from "../ui";

export function Profile({ me, run, busy, notify, refresh, onThemeChange }) {
  const dark = me.theme === "dark";
  const [edit, setEdit] = useState(false),
    [passwordOpen, setPasswordOpen] = useState(false),
    [currentPassword, setCurrentPassword] = useState(""),
    [newPassword, setNewPassword] = useState(""),
    [repeatPassword, setRepeatPassword] = useState(""),
    [field, setField] = useState("name"),
    [value, setValue] = useState(""),
    [reason, setReason] = useState(""),
    [schedules, setSchedules] = useState([]);
  useEffect(() => {
    run(async () => setSchedules(await api(`/people/${me.id}/schedules`)));
  }, []);
  const direct = ["Suporte", "Diretoria"].includes(me.role);
  return (
    <section className="profile-sheet sheet">
      <div className="profile-name">
        <span className="avatar large">{me.name[0]}</span>
        <div>
          <h2>{me.name}</h2>
          <p>{me.role}</p>
        </div>
      </div>
      <div className="theme-preference">
        <span>Light Mode</span>
        <button
          type="button"
          className="theme-switch"
          role="switch"
          aria-label="Dark Mode"
          aria-checked={dark}
          disabled={busy}
          onClick={() =>
            run(async () => {
              const user = await api(
                "/profile/theme",
                { theme: dark ? "light" : "dark" },
                "PUT",
              );
              onThemeChange(user);
            })
          }
        >
          <span>
            <Sun size={16} className="theme-sun" />
            <Moon size={16} className="theme-moon" />
          </span>
        </button>
        <span>Dark Mode</span>
      </div>
      <dl className="facts">
        <dt>E-mail</dt>
        <dd>{me.details.email || "—"}</dd>
        <dt>Telefone</dt>
        <dd>{phoneFormat(me.details.phone) || "—"}</dd>
        <dt>Nascimento</dt>
        <dd>{dateLabel(me.details.birth)}</dd>
        <dt>Login</dt>
        <dd>{me.login}</dd>
      </dl>
      <Button
        className="secondary"
        onClick={() => {
          setValue("");
          setEdit(true);
        }}
      >
        {direct ? "Editar meus dados" : "Solicitar alteração"}
      </Button>
      <Button
        className="secondary"
        onClick={() => {
          setCurrentPassword("");
          setNewPassword("");
          setRepeatPassword("");
          setPasswordOpen(true);
        }}
      >
        Alterar minha senha
      </Button>
      {passwordOpen && (
        <Modal title="Alterar minha senha" close={() => setPasswordOpen(false)}>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              run(async () => {
                if (newPassword !== repeatPassword)
                  throw new Error("As senhas não conferem.");
                await api("/password", {
                  current: currentPassword,
                  password: newPassword,
                });
                setPasswordOpen(false);
                notify("Senha atualizada");
              });
            }}
          >
            <Password
              label="Senha atual"
              autoComplete="current-password"
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
              required
            />
            <Password
              label="Nova senha"
              autoComplete="new-password"
              minLength={8}
              maxLength={128}
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              required
            />
            <Password
              label="Confirmar nova senha"
              autoComplete="new-password"
              minLength={8}
              maxLength={128}
              value={repeatPassword}
              onChange={(e) => setRepeatPassword(e.target.value)}
              required
            />
            <Button className="primary" busy={busy}>
              Salvar nova senha
            </Button>
          </form>
        </Modal>
      )}
      {schedules.length > 0 && (
        <details>
          <summary>Minha jornada</summary>
          {schedules
            .filter(
              (s, i, a) =>
                s.effective >= dateNow() ||
                i === a.findIndex((x) => x.effective <= dateNow()),
            )
            .map((s) => (
              <div key={s.id} className="history-line">
                <strong>Vigência: {dateLabel(s.effective)}</strong>
                {Object.entries(s.days).map(
                  ([day, p]) =>
                    p.length > 0 && (
                      <span key={day}>
                        {days[day]} · {p.map((x) => x.join("–")).join(" / ")}
                      </span>
                    ),
                )}
              </div>
            ))}
        </details>
      )}
      {me.role === "Professor" && (
        <details>
          <summary>Grade pedagógica</summary>
          {(me.details.lessons || []).map((l, i) => (
            <p key={i}>
              {days[l.day]} · {l.start}–{l.end} · {l.class} · {l.subject}
            </p>
          ))}
        </details>
      )}
      {edit && (
        <Modal
          title={direct ? "Editar meus dados" : "Solicitar alteração"}
          close={() => setEdit(false)}
        >
          <form
            onSubmit={(e) => {
              e.preventDefault();
              run(async () => {
                if (direct) {
                  await api("/profile", { [field]: value }, "PUT");
                  await refresh();
                } else
                  await api("/requests", {
                    type: "profile",
                    field,
                    value,
                    reason,
                  });
                setEdit(false);
                notify(direct ? "Dados atualizados" : "Solicitação em análise");
              });
            }}
          >
            <Field label="Campo">
              <select value={field} onChange={(e) => setField(e.target.value)}>
                {Object.entries({
                  name: "Nome",
                  email: "E-mail",
                  phone: "Telefone",
                  birth: "Nascimento",
                }).map(([k, v]) => (
                  <option key={k} value={k}>
                    {v}
                  </option>
                ))}
              </select>
            </Field>
            <Field
              label="Novo valor"
              type={
                field === "birth"
                  ? "date"
                  : field === "email"
                    ? "email"
                    : "text"
              }
              value={field === "phone" ? phoneFormat(value) : value}
              onChange={(e) =>
                setValue(
                  field === "phone"
                    ? e.target.value.replace(/\D/g, "").slice(0, 11)
                    : e.target.value,
                )
              }
              required
            />
            {!direct && (
              <Field label="Motivo">
                <textarea
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                  required
                />
              </Field>
            )}
            <Button className="primary" busy={busy}>
              {direct ? "Salvar" : "Enviar solicitação"}
            </Button>
          </form>
        </Modal>
      )}
    </section>
  );
}
