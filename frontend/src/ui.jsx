import React, { useState, useEffect, useRef } from "react";
import { Eye, EyeOff, X, LoaderCircle } from "lucide-react";
export const roles = [
  "Colaborador",
  "Professor",
  "Administração",
  "Diretoria",
  "Suporte",
];
export const days = [
  "Segunda",
  "Terça",
  "Quarta",
  "Quinta",
  "Sexta",
  "Sábado",
  "Domingo",
];
export const classes = [
  "Jardim",
  "Pré",
  "1º Ano A",
  "1º Ano B",
  "2º Ano A",
  "2º Ano B",
  "3º Ano A",
  "3º Ano B",
  "4º Ano A",
  "5º Ano A",
  "5º Ano B",
  "6º Ano A",
  "7º Ano A",
  "8º Ano A",
  "8º Ano B",
  "9º Ano A",
  "1ª Série",
  "2ª Série",
  "3ª Série",
];
export const dateNow = () =>
  new Intl.DateTimeFormat("en-CA", {
    timeZone: "America/Sao_Paulo",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(new Date());
export const dateLabel = (d) => (d ? d.split("-").reverse().join("/") : "—");
export const hours = (v) =>
  v === null || v === undefined
    ? "—"
    : `${v < 0 ? "−" : ""}${Math.floor(Math.abs(v) / 60)}h${String(Math.abs(v) % 60).padStart(2, "0")}`;
export async function api(path, data, method) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 30000);
  try {
    const response = await fetch("/api" + path, {
      method: method || (data === undefined ? "GET" : "POST"),
      headers: { "Content-Type": "application/json", "X-Ponto": "1" },
      credentials: "same-origin",
      cache: "no-store",
      signal: controller.signal,
      body: data === undefined ? undefined : JSON.stringify(data),
    });
    if (!response.ok) {
      const json = await response.json().catch(() => ({}));
      let message =
        typeof json.detail === "string"
          ? json.detail
          : Array.isArray(json.detail)
            ? "Confira os campos preenchidos."
            : "Não foi possível concluir esta ação. Tente novamente.";
      if (json.reference) message += " Referência: " + json.reference;
      const error = new Error(message);
      error.status = response.status;
      throw error;
    }
    if (response.headers.get("content-type")?.includes("spreadsheet"))
      return response.blob();
    if (!response.headers.get("content-type")?.includes("application/json"))
      throw new Error("Atualize a página para continuar.");
    return await response.json();
  } catch (error) {
    if (error.name === "AbortError")
      throw new Error(
        "A resposta demorou. Confira seus registros antes de tentar novamente.",
      );
    if (error instanceof TypeError)
      throw new Error("Sem conexão. Confira sua internet e tente novamente.");
    throw error;
  } finally {
    clearTimeout(timer);
  }
}
export function phoneFormat(value = "") {
  const v = String(value).replace(/\D/g, "").slice(0, 11);
  if (v.length <= 2) return v;
  const local = v.slice(2),
    cut = local.length > 8 ? 5 : 4;
  return (
    v.slice(0, 2) +
    " " +
    local.slice(0, cut) +
    (local.length > cut ? "-" + local.slice(cut) : "")
  );
}
export function Field({ label, children, ...props }) {
  return (
    <label className="field">
      <span>{label}</span>
      {children || <input {...props} />}
    </label>
  );
}
export function Password({ label = "Senha", ...props }) {
  const [show, set] = useState(false);
  return (
    <Field label={label}>
      <div className="password">
        <input {...props} type={show ? "text" : "password"} />
        <button
          type="button"
          aria-label={show ? "Ocultar senha" : "Mostrar senha"}
          onClick={() => set(!show)}
        >
          {show ? <EyeOff size={19} /> : <Eye size={19} />}
        </button>
      </div>
    </Field>
  );
}
export function Button({ busy, children, ...props }) {
  return (
    <button {...props} disabled={props.disabled || busy}>
      {busy && <LoaderCircle size={18} className="spin" />}
      {children}
    </button>
  );
}
export function Empty({ children = "Nenhum registro encontrado." }) {
  return <p className="empty">{children}</p>;
}
export function Modal({ title, close, children, wide = false }) {
  const ref = useRef(),
    [error, setError] = useState("");
  useEffect(() => {
    const old = document.activeElement;
    ref.current.showModal();
    const handle = (e) => setError(e.detail);
    window.addEventListener("ponto-error", handle);
    return () => {
      window.removeEventListener("ponto-error", handle);
      old?.focus();
    };
  }, []);
  return (
    <dialog
      ref={ref}
      className={wide ? "wide" : ""}
      onCancel={(e) => {
        e.preventDefault();
        close();
      }}
    >
      <header>
        <h2>{title}</h2>
        <button className="icon" aria-label="Fechar" onClick={close}>
          <X />
        </button>
      </header>
      {error && (
        <div className="inline-error" role="alert">
          {error}
          <button onClick={() => setError("")}>×</button>
        </div>
      )}
      {children}
    </dialog>
  );
}
export function SuccessToast({ message }) {
  const ref = useRef();
  useEffect(() => {
    const element = ref.current;
    element.showPopover?.();
    return () => element.hidePopover?.();
  }, [message]);
  return (
    <div
      ref={ref}
      popover="manual"
      className="toast success-toast"
      role="status"
    >
      {message}
    </div>
  );
}

export function Tabs({ items, value, onChange }) {
  return (
    <div className="tabs">
      {items.map((t) => (
        <button
          type="button"
          key={t}
          onClick={() => onChange(t)}
          className={value === t ? "active" : ""}
        >
          {t}
        </button>
      ))}
    </div>
  );
}
export function Notice({ children }) {
  return (
    <div className="notice" role="status">
      {children}
    </div>
  );
}
