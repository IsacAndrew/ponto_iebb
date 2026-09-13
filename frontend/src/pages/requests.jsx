import React, { useState, useEffect } from "react";
import { ChevronRight } from "lucide-react";

import { api, Field, Button, Modal, Empty, Notice, dateLabel } from "../ui";

export function Requests({ run, busy, notify, admin }) {
  const [rows, setRows] = useState([]),
    [approved, setApproved] = useState(false),
    [name, setName] = useState(""),
    [start, setStart] = useState(""),
    [end, setEnd] = useState(""),
    [selected, setSelected] = useState(null),
    [reason, setReason] = useState("");
  const load = async () => setRows(await api("/requests"));
  useEffect(() => {
    run(load);
  }, []);
  const visible = rows.filter(
    (r) =>
      (approved ? r.status === "Aprovada" : r.status !== "Aprovada") &&
      (!name || r.name.toLowerCase().includes(name.toLowerCase())) &&
      (!start || r.date >= start) &&
      (!end || r.date <= end),
  );
  return (
    <>
      <div className="toolbar">
        <Button className="secondary" onClick={() => setApproved(!approved)}>
          {approved ? "Voltar às pendentes" : "Solicitações aprovadas"}
        </Button>
        {approved && (
          <>
            <Field
              label="Nome"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
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
          </>
        )}
      </div>
      <section className="sheet">
        {!visible.length && <Empty>Não há solicitações.</Empty>}
        {visible.map((r) => (
          <button
            key={r.id}
            className="list-row"
            onClick={() => {
              setSelected(r);
              setReason("");
            }}
          >
            <div>
              <strong>
                {r.data.type === "point"
                  ? "Correção de ponto"
                  : "Alteração cadastral"}
              </strong>
              <span>
                {r.name} · {dateLabel(r.date)}
              </span>
            </div>
            <span>{r.status}</span>
            <ChevronRight size={18} />
          </button>
        ))}
        {selected && (
          <Modal title="Solicitação" close={() => setSelected(null)}>
            <p>
              <strong>{selected.name}</strong>
            </p>
            {selected.data.type === "point" ? (
              <dl className="facts">
                <dt>Anterior</dt>
                <dd>
                  {selected.data.before.punches
                    .map((p) => p.time)
                    .join(" · ") || "Sem marcações"}
                </dd>
                <dt>Solicitado</dt>
                <dd>
                  {selected.data.times.join(" · ") || "Remover marcações"}
                </dd>
              </dl>
            ) : (
              <dl className="facts">
                <dt>Campo</dt>
                <dd>
                  {
                    {
                      name: "Nome",
                      email: "E-mail",
                      phone: "Telefone",
                      birth: "Nascimento",
                    }[selected.data.field]
                  }
                </dd>
                <dt>Anterior</dt>
                <dd>{selected.data.before.value || "—"}</dd>
                <dt>Solicitado</dt>
                <dd>{selected.data.value}</dd>
              </dl>
            )}
            <p>{selected.data.reason}</p>
            {selected.data.decision_reason && (
              <Notice>
                {selected.status} por {selected.data.decision_by}:{" "}
                {selected.data.decision_reason}
              </Notice>
            )}
            {admin && selected.status === "Pendente" && (
              <>
                <Field label="Motivo da decisão">
                  <textarea
                    value={reason}
                    onChange={(e) => setReason(e.target.value)}
                  />
                </Field>
                <div className="actions">
                  {[false, true].map((approve) => (
                    <Button
                      key={String(approve)}
                      className={approve ? "primary" : "secondary"}
                      busy={busy}
                      onClick={() =>
                        run(async () => {
                          await api(`/requests/${selected.id}/decide`, {
                            approve,
                            reason,
                          });
                          setSelected(null);
                          await load();
                          notify("Decisão registrada");
                        })
                      }
                    >
                      {approve ? "Aprovar" : "Reprovar"}
                    </Button>
                  ))}
                </div>
              </>
            )}
          </Modal>
        )}
      </section>
    </>
  );
}
