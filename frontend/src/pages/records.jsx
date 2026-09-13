import React, { useState, useEffect } from "react";
import { Plus, ChevronRight } from "lucide-react";

import { api, Field, Button, Empty, dateNow, dateLabel, hours } from "../ui";

export function Records({
  run,
  busy,
  notify,
  administrative = false,
  me,
  personId,
}) {
  const [start, setStart] = useState(dateNow()),
    [end, setEnd] = useState(dateNow()),
    [rows, setRows] = useState([]),
    [expanded, setExpanded] = useState(null),
    [clock, setClock] = useState(Date.now());
  const pid = personId || me.id,
    load = async () =>
      setRows(await api(`/records?start=${start}&end=${end}&person_id=${pid}`));
  useEffect(() => {
    run(load);
  }, [pid]);
  useEffect(() => {
    const timer = setInterval(() => setClock(Date.now()), 1000);
    return () => clearInterval(timer);
  }, []);
  const worked = (row) => {
    if (row.date !== dateNow() || row.punches.length % 2 === 0)
      return hours(row.worked);
    const punch = row.punches[row.punches.length - 1],
      started = punch.epoch * 1000 || Date.parse(punch.at),
      seconds = Math.max(
        0,
        Math.floor(row.worked * 60 + (clock - started) / 1000),
      );
    return `${Math.floor(seconds / 3600)}h${String(Math.floor((seconds % 3600) / 60)).padStart(2, "0")}m${String(seconds % 60).padStart(2, "0")}s`;
  };
  const max = Math.max(0, ...rows.map((r) => r.punches.length));
  return (
    <>
      <form
        className="toolbar compact"
        onSubmit={(e) => {
          e.preventDefault();
          run(load);
        }}
      >
        <Field
          label="De"
          type="date"
          value={start}
          onChange={(e) => setStart(e.target.value)}
        />
        <Field
          label="Até"
          type="date"
          value={end}
          onChange={(e) => setEnd(e.target.value)}
        />
        <Button className="primary" busy={busy}>
          Consultar
        </Button>
      </form>
      <section className="sheet table-wrap">
        <table>
          <thead>
            <tr>
              <th>Data</th>
              {Array.from({ length: max }, (_, i) => (
                <th key={i}>{i + 1}ª marcação</th>
              ))}
              <th>Horas trabalhadas</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <React.Fragment key={r.date}>
                <tr>
                  <td>{dateLabel(r.date)}</td>
                  {Array.from({ length: max }, (_, i) => (
                    <td className="times" key={i}>
                      {r.punches[i]?.time || "—"}
                    </td>
                  ))}
                  <td className="times">{worked(r)}</td>
                  <td>
                    <button
                      className="icon"
                      aria-label="Ver detalhes"
                      onClick={() =>
                        setExpanded(expanded === r.date ? null : r.date)
                      }
                    >
                      <ChevronRight
                        className={expanded === r.date ? "open-chevron" : ""}
                        size={18}
                      />
                    </button>
                  </td>
                </tr>
                {expanded === r.date && (
                  <tr className="detail-row">
                    <td colSpan={max + 3}>
                      <dl className="facts">
                        <dt>Jornada</dt>
                        <dd>
                          {r.periods.map((x) => x.join("–")).join(" / ") ||
                            "Sem expediente"}
                        </dd>
                        <dt>Atraso</dt>
                        <dd>{hours(r.late)}</dd>
                        <dt>Hora extra</dt>
                        <dd>{hours(r.extra)}</dd>
                        <dt>Horas negativas</dt>
                        <dd>{hours(r.negative)}</dd>
                        <dt>Saldo</dt>
                        <dd>{hours(r.balance)}</dd>
                        <dt>Situação</dt>
                        <dd>{r.status}</dd>
                      </dl>
                      <RecordActions
                        row={r}
                        administrative={
                          administrative ||
                          ["Suporte", "Diretoria"].includes(me.role)
                        }
                        run={run}
                        busy={busy}
                        notify={notify}
                        reload={load}
                      />
                    </td>
                  </tr>
                )}
              </React.Fragment>
            ))}
          </tbody>
        </table>
        {!rows.length && <Empty />}
      </section>
    </>
  );
}
function RecordActions({ row, administrative, run, busy, notify, reload }) {
  const [edit, setEdit] = useState(false),
    [times, setTimes] = useState(row.punches.map((p) => p.time)),
    [reason, setReason] = useState("");
  if (!edit)
    return (
      <Button className="secondary" onClick={() => setEdit(true)}>
        {administrative ? "Corrigir marcações" : "Solicitar correção"}
      </Button>
    );
  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        run(async () => {
          await api(administrative ? "/corrections" : "/requests", {
            person_id: row.person_id,
            date: row.date,
            times,
            reason,
            type: "point",
          });
          notify(
            administrative ? "Marcações corrigidas" : "Solicitação enviada",
          );
          setEdit(false);
          await reload();
        });
      }}
    >
      <div className="time-editor">
        {times.map((t, i) => (
          <div key={i}>
            <input
              type="time"
              aria-label={`Marcação ${i + 1}`}
              value={t}
              onChange={(e) =>
                setTimes(times.map((v, j) => (i === j ? e.target.value : v)))
              }
            />
            <button
              type="button"
              className="icon"
              onClick={() => setTimes(times.filter((_, j) => j !== i))}
            >
              ×
            </button>
          </div>
        ))}
      </div>
      <button
        type="button"
        className="text-button"
        onClick={() => setTimes([...times, ""])}
      >
        <Plus size={16} />
        Adicionar horário
      </button>
      <Field label="Motivo">
        <textarea
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          required
        />
      </Field>
      <Button className="primary" busy={busy}>
        Salvar
      </Button>
    </form>
  );
}
