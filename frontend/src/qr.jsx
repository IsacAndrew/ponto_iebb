import React, { useEffect, useRef, useState } from "react";
import { api, Button } from "./ui";
import { applyTheme } from "./theme";
import { locate, warmLocation } from "./location";
export function QRAccess() {
  const token = decodeURIComponent(location.pathname.slice(3)),
    [state, setState] = useState(null),
    [clock, setClock] = useState(new Date()),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false),
    [question, setQuestion] = useState(null),
    [done, setDone] = useState(null);
  const draft = useRef(null),
    lock = useRef(false),
    offset = useRef(0);
  const load = async () => {
    try {
      const data = await api("/qr/" + token);
      const account = await api("/me");
      applyTheme(account.user.theme);
      setState(data);
      offset.current = new Date(data.now).getTime() - Date.now();
      if (data.location_required !== false) warmLocation();
    } catch (e) {
      if ([401, 403, 409].includes(e.status)) {
        sessionStorage.setItem("ponto_qr_return", location.pathname);
        location.href = "/";
        return;
      }
      setError(e.message);
    }
  };
  useEffect(() => {
    load();
    const timer = setInterval(
      () => setClock(new Date(Date.now() + offset.current)),
      1000,
    );
    return () => clearInterval(timer);
  }, []);
  const send = async (extra) => {
    if (lock.current) return;
    lock.current = true;
    setBusy(true);
    setError("");
    try {
      const payload = {
        ...(draft.current || { key: crypto.randomUUID() }),
        ...extra,
      };
      if (state?.location_required !== false) {
        const position = await locate();
        payload.lat = position.coords.latitude;
        payload.lon = position.coords.longitude;
        payload.accuracy = position.coords.accuracy;
      }
      draft.current = payload;
      const result = await api("/qr/" + token + "/punch", payload);
      if (result.question) {
        setQuestion(result);
        return;
      }
      setDone(result);
      draft.current = null;
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
      lock.current = false;
    }
  };
  if (done)
    return (
      <main className="qr-success">
        <time>{done.registered_at}</time>
        <h1>{done.confirmation}</h1>
        <p>Pode fechar esta página</p>
        <a href="/" className="secondary">
          Voltar ao meu ponto
        </a>
      </main>
    );
  return (
    <main className="qr-access">
      {state ? (
        <>
          <h1>Olá, {state.name}</h1>
          <div className="qr-clock">
            {clock.toLocaleTimeString("pt-BR", {
              timeZone: "America/Sao_Paulo",
              hour: "2-digit",
              minute: "2-digit",
            })}
            <small>
              {clock.toLocaleTimeString("pt-BR", {
                timeZone: "America/Sao_Paulo",
                second: "2-digit",
              })}
            </small>
          </div>
          <Button
            className="primary qr-button"
            busy={busy}
            disabled={!state.can_register}
            onClick={() => send({})}
          >
            {state.next}
          </Button>
          {error && <p className="inline-error">{error}</p>}
          {question && (
            <div className="qr-question">
              <p>{question.message}</p>
              <Button
                className="secondary"
                disabled={busy}
                onClick={() => {
                  if (question.question === "forgot") send({ forgot: "no" });
                  else {
                    setQuestion(null);
                    draft.current = null;
                  }
                }}
              >
                Não
              </Button>
              <Button
                className="primary"
                busy={busy}
                onClick={() =>
                  send(
                    question.question === "forgot"
                      ? { forgot: "yes" }
                      : { overtime: true },
                  )
                }
              >
                Sim
              </Button>
            </div>
          )}
        </>
      ) : (
        <p>{error || "Carregando…"}</p>
      )}
    </main>
  );
}
