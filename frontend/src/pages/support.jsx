import React, { useState, useEffect } from "react";
import { ChevronRight } from "lucide-react";

import { api, Field, Button, Modal, Empty, dateLabel } from "../ui";

export function Support({ run, busy, notify }) {
  const [rows, setRows] = useState([]),
    [selected, setSelected] = useState(null),
    [reason, setReason] = useState(""),
    [completed, setCompleted] = useState(false),
    [locationRequired, setLocationRequired] = useState(true);
  const load = async () => setRows(await api("/support/occurrences"));
  useEffect(() => {
    run(async () => {
      await load();
      setLocationRequired((await api("/support/my-location")).required);
    });
  }, []);
  const visible = rows.filter((r) => completed || r.status === "Pendente");
  return (
    <>
      <div className="toolbar">
        <label className="check">
          <input
            type="checkbox"
            checked={locationRequired}
            onChange={(e) => {
              const required = e.target.checked;
              setLocationRequired(required);
              run(async () => {
                await api("/support/my-location", { required }, "PUT");
                notify("Preferência de localização salva");
              });
            }}
          />
          Exigir localização para minha conta
        </label>
        <label className="check">
          <input
            type="checkbox"
            checked={completed}
            onChange={(e) => setCompleted(e.target.checked)}
          />
          Incluir concluídas
        </label>
      </div>
      <section className="sheet">
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
              <strong>{r.data.title}</strong>
              <span>
                {r.name} · {dateLabel(r.date)}
              </span>
            </div>
            <span>{r.status}</span>
            <ChevronRight size={18} />
          </button>
        ))}
        {!visible.length && <Empty>Nenhuma ocorrência pendente.</Empty>}
      </section>
      {selected && (
        <Modal title={selected.data.title} close={() => setSelected(null)}>
          <p>
            {selected.name} · {dateLabel(selected.date)}
          </p>
          {selected.status === "Pendente" ? (
            <>
              <Field label="Resultado da análise">
                <textarea
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                />
              </Field>
              <div className="actions">
                {(selected.data.title === "Hora extra pendente"
                  ? [false, true]
                  : [true]
                ).map((approve) => (
                  <Button
                    className={approve ? "primary" : "secondary"}
                    key={String(approve)}
                    busy={busy}
                    onClick={() =>
                      run(async () => {
                        await api("/support/occurrences/" + selected.id, {
                          approve,
                          reason,
                        });
                        setSelected(null);
                        await load();
                        notify("Análise registrada");
                      })
                    }
                  >
                    {selected.data.title === "Hora extra pendente"
                      ? approve
                        ? "Validar extra"
                        : "Não validar"
                      : "Concluir"}
                  </Button>
                ))}
              </div>
            </>
          ) : (
            <p>{selected.data.resolution}</p>
          )}
        </Modal>
      )}
    </>
  );
}
