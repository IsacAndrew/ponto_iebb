import React, { useState, useRef, useEffect } from "react";
import {
  Fingerprint,
  Check,
  MapPin,
  Clock3,
  Coffee,
  ArrowUpRight,
  CalendarDays,
  CircleCheck,
  AlertCircle,
} from "lucide-react";
import { api, Button, Modal, hours } from "../ui";
import { locate } from "../location";

export function Punch({ me, run, busy, notify, initial, onNavigate }) {
  const [day, setDay] = useState(initial),
    [clock, setClock] = useState(() => new Date(initial?.now || Date.now())),
    [geo, setGeo] = useState(""),
    [question, setQuestion] = useState(null),
    [success, setSuccess] = useState(false),
    [submitting, setSubmitting] = useState(false);
  const offset = useRef(0),
    draft = useRef(null),
    lock = useRef(false),
    revision = useRef(0),
    successTimer = useRef();
  useEffect(() => {
    if (initial) {
      setDay(initial);
      offset.current = Date.parse(initial.now) - Date.now();
      setClock(new Date(initial.now));
    }
  }, [initial]);
  useEffect(() => {
    let active = true;
    const load = async () => {
      const version = revision.current;
      const value = await api("/punch/today");
      if (active && version === revision.current) {
        setDay(value);
        offset.current = Date.parse(value.now) - Date.now();
        setClock(new Date(value.now));
      }
    };
    if (!initial) run(load);
    const clockTimer = setInterval(
      () => setClock(new Date(Date.now() + offset.current)),
      1000,
    );
    const poll = setInterval(() => {
      if (document.visibilityState === "visible" && !lock.current)
        load().catch(() => {});
    }, 30000);
    return () => {
      active = false;
      clearInterval(clockTimer);
      clearInterval(poll);
      clearTimeout(successTimer.current);
    };
  }, []);
  const send = async (additions) => {
    if (lock.current) return;
    lock.current = true;
    revision.current++;
    setSubmitting(true);
    setGeo("");
    try {
      await run(async () => {
        if (day?.location_required !== false && day?.geo_ready === false)
          throw new Error(
            "A escola precisa confirmar o local de registro. Procure o Suporte.",
          );
        const payload = {
          ...(draft.current || { key: crypto.randomUUID() }),
          ...additions,
        };
        draft.current = payload;
        if (day?.location_required !== false) {
          try {
            const position = await locate();
            Object.assign(payload, {
              lat: position.coords.latitude,
              lon: position.coords.longitude,
              accuracy: position.coords.accuracy,
            });
          } catch (error) {
            setGeo(error.message);
            return;
          }
        }
        let result;
        try {
          result = await api("/punch", payload);
        } catch (error) {
          if (error.status === 422) {
            setGeo(error.message);
            return;
          }
          throw error;
        }
        if (result.question) {
          setQuestion(result);
          return;
        }
        setDay((previous) => ({ ...previous, ...result.day }));
        setQuestion(null);
        draft.current = null;
        setSuccess(true);
        notify(result.message);
        successTimer.current = setTimeout(() => setSuccess(false), 4000);
      });
    } finally {
      lock.current = false;
      setSubmitting(false);
    }
  };
  const expected = day?.periods.flat() || [],
    punches = day?.punches || [],
    index = punches.length,
    done = !!day && index >= expected.length,
    working = index % 2 === 1;
  const labels =
    expected.length === 4
      ? ["Entrada", "Intervalo", "Retorno", "Saída"]
      : expected.map((_, i) => (i % 2 ? "Saída" : "Entrada"));
  const date = clock.toLocaleDateString("pt-BR", {
    timeZone: "America/Sao_Paulo",
    weekday: "long",
    day: "numeric",
    month: "long",
  });
  let worked = day?.worked || 0;
  if (working && punches[index - 1]?.epoch)
    worked += Math.max(
      0,
      Math.floor((clock.getTime() / 1000 - punches[index - 1].epoch) / 60),
    );
  return (
    <div className="punch-dashboard">
      <div className="greeting">
        <span className="eyebrow">SUA ROTINA, EM DIA</span>
        <h1>
          Olá, {me.name.split(" ")[0]}
          <span className="greeting-dot">.</span>
        </h1>
        <p>Acompanhe sua jornada e registre seu ponto por aqui.</p>
      </div>
      <div className="punch-grid">
        <section className="punch-card">
          <div className="card-topline">
            <span>
              <CalendarDays size={17} />
              Meu ponto
            </span>
            <span className={"status-pill " + (working ? "live" : "")}>
              {working
                ? "Em expediente"
                : index
                  ? "Registro atualizado"
                  : "Pronto para começar"}
            </span>
          </div>
          <div className="clock-block">
            <p className="clock-date">{date}</p>
            <div className="clock" aria-label="Horário de Brasília">
              {clock.toLocaleTimeString("pt-BR", {
                timeZone: "America/Sao_Paulo",
                hour: "2-digit",
                minute: "2-digit",
              })}
              <span>
                {clock.toLocaleTimeString("pt-BR", {
                  timeZone: "America/Sao_Paulo",
                  second: "2-digit",
                })}
              </span>
            </div>
            <span className="timezone-label">Horário de Brasília</span>
          </div>
          <div className="next-action">
            <span className="next-icon">
              {working ? <Coffee size={20} /> : <Fingerprint size={22} />}
            </span>
            <div>
              <small>PRÓXIMO REGISTRO</small>
              <strong>
                {!day
                  ? "Carregando jornada…"
                  : done
                    ? working
                      ? "Saída de hora extra"
                      : expected.length
                        ? "Jornada concluída"
                        : "Sem jornada cadastrada"
                    : labels[index]}
              </strong>
            </div>
            {!done && day && <time>{expected[index]}</time>}
          </div>
          <Button
            className={"primary punch-button " + (success ? "success" : "")}
            busy={submitting}
            disabled={!day || (done && !working)}
            onClick={() => send({})}
          >
            {success ? (
              <>
                <Check size={22} />
                Ponto registrado
              </>
            ) : submitting ? (
              "Confirmando seu registro…"
            ) : done && !working ? (
              <>
                <CircleCheck size={21} />
                {expected.length
                  ? "Tudo certo por hoje"
                  : "Sem jornada prevista"}
              </>
            ) : (
              <>
                <Fingerprint size={24} />
                Registrar ponto
                <ArrowUpRight size={20} />
              </>
            )}
          </Button>
          <p className="location-hint">
            <MapPin size={15} />
            {day?.location_required === false
              ? "Localização dispensada para este acesso"
              : "Localização verificada no momento do registro"}
          </p>
          {done && !working && expected.length > 0 && (
            <button
              className="text-button extra-action"
              onClick={() => {
                draft.current = null;
                setQuestion({
                  question: "overtime",
                  message: "Você está fazendo hora extra?",
                });
              }}
            >
              Registrar hora extra
              <ArrowUpRight size={15} />
            </button>
          )}
          {day && !expected.length && (
            <p className="muted">
              Confira sua jornada com o responsável pelos cadastros.
            </p>
          )}
        </section>
        <aside className="day-panel">
          <section className="sheet journey-card">
            <div className="section-heading">
              <h2>Sua jornada hoje</h2>
              <Clock3 size={19} />
            </div>
            <p className="muted">
              {day?.holiday || "Um registro de cada vez."}
            </p>
            <ol className="journey-timeline">
              {expected.map((time, i) => (
                <li
                  key={i}
                  className={
                    i < index ? "completed" : i === index ? "current" : ""
                  }
                >
                  <span className="timeline-dot">
                    {i < index ? <Check size={13} /> : i + 1}
                  </span>
                  <div>
                    <strong>{labels[i]}</strong>
                    <small>{i < index ? "Registrado" : "Previsto"}</small>
                  </div>
                  <time>{punches[i]?.time || time}</time>
                </li>
              ))}
            </ol>
            {!expected.length && (
              <div className="empty">Nenhum período previsto para hoje.</div>
            )}
            {punches.slice(expected.length).map((p, i) => (
              <div className="extra-punch" key={p.key || i}>
                <span>Extra · {i % 2 ? "Saída" : "Entrada"}</span>
                <strong>{p.time}</strong>
              </div>
            ))}
          </section>
          <button
            className="history-link"
            onClick={() => onNavigate("Meus Registros")}
          >
            <div>
              <strong>Precisa conferir outro dia?</strong>
              <span>Acesse seu histórico de registros</span>
            </div>
            <ArrowUpRight size={22} />
          </button>
        </aside>
      </div>
      <section className="day-stats" aria-label="Resumo do dia">
        <div>
          <span className="stat-icon">
            <Clock3 size={20} />
          </span>
          <div>
            <small>Horas trabalhadas</small>
            <strong>{day ? hours(worked) : "—"}</strong>
          </div>
        </div>
        <div>
          <span className="stat-icon">
            <CalendarDays size={20} />
          </span>
          <div>
            <small>Jornada prevista</small>
            <strong>{day ? hours(day.planned) : "—"}</strong>
          </div>
        </div>
        <div>
          <span className="stat-icon">
            <CircleCheck size={20} />
          </span>
          <div>
            <small>Marcações realizadas</small>
            <strong>
              {day ? String(index).padStart(2, "0") : "—"}
              <small> / {expected.length}</small>
            </strong>
          </div>
        </div>
      </section>
      {geo && (
        <section className="location-card" role="alert">
          <AlertCircle />
          <div>
            <h2>Vamos conferir sua localização</h2>
            <p>{geo}</p>
            <Button className="secondary" busy={busy} onClick={() => send({})}>
              Tentar novamente
            </Button>
          </div>
        </section>
      )}
      {question && (
        <Modal
          title={question.message}
          close={() => {
            setQuestion(null);
            draft.current = null;
          }}
        >
          <p>Essa informação ajuda o Suporte a acompanhar sua jornada.</p>
          <div className="actions">
            <Button
              className="secondary"
              onClick={() => {
                const q = question;
                setQuestion(null);
                if (q.question === "forgot") send({ forgot: "no" });
                else draft.current = null;
              }}
            >
              Não
            </Button>
            <Button
              className="primary"
              busy={busy}
              onClick={() => {
                const q = question;
                setQuestion(null);
                send(
                  q.question === "forgot"
                    ? { forgot: "yes" }
                    : { overtime: true },
                );
              }}
            >
              Sim, continuar
            </Button>
          </div>
        </Modal>
      )}
    </div>
  );
}
