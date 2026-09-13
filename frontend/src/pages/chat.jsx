import React, { useState, useEffect } from "react";
import { Send } from "lucide-react";

import { api, Button, Modal, Empty } from "../ui";

export function Chat({ me, run, busy, management = false }) {
  const [rows, setRows] = useState([]),
    [id, setId] = useState(null),
    [message, setMessage] = useState(""),
    [closing, setClosing] = useState(false);
  const load = async () =>
    setRows(await api("/tickets" + (management ? "?management=true" : "")));
  useEffect(() => {
    run(load);
    const timer = setInterval(() => {
      if (document.visibilityState === "visible") load().catch(() => {});
    }, 15000);
    return () => clearInterval(timer);
  }, []);
  const selected =
    rows.find((r) => r.id === id) || (!management ? rows[0] : null);
  return (
    <div className="chat-layout">
      {management && (
        <div className="ticket-list">
          {rows.map((r) => (
            <button
              key={r.id}
              className={`list-row ${selected?.id === r.id ? "active" : ""}`}
              onClick={() => setId(r.id)}
            >
              <strong>{r.name}</strong>
            </button>
          ))}
          {!rows.length && <Empty>Não há chamados abertos.</Empty>}
        </div>
      )}
      <div className="conversation">
        {selected && (
          <div className="chat-head">
            <strong>{selected.name}</strong>
            {management && (
              <button className="text-button" onClick={() => setClosing(true)}>
                Concluir chamado
              </button>
            )}
          </div>
        )}
        <div className="messages">
          {selected?.data.messages.map((m, i) => (
            <div
              key={i}
              className={`message ${m.support ? "support-message" : ""}`}
            >
              <strong>{m.name}</strong>
              <p>{m.text}</p>
              <time>
                {new Date(m.at).toLocaleTimeString("pt-BR", {
                  hour: "2-digit",
                  minute: "2-digit",
                })}
              </time>
            </div>
          ))}
          {!selected && (
            <Empty>
              {management
                ? "Selecione um chamado para atender."
                : "Como o Suporte pode ajudar?"}
            </Empty>
          )}
        </div>
        {(!management || selected) && (
          <form
            className="chat-input"
            onSubmit={(e) => {
              e.preventDefault();
              run(async () => {
                await api(
                  selected ? `/tickets/${selected.id}/message` : "/tickets",
                  { message },
                );
                setMessage("");
                await load();
              });
            }}
          >
            <textarea
              aria-label="Mensagem"
              placeholder="Escreva sua mensagem"
              value={message}
              maxLength={4000}
              onChange={(e) => setMessage(e.target.value)}
              required
            />
            <Button
              className="primary"
              busy={busy}
              aria-label="Enviar mensagem"
            >
              <Send size={19} />
            </Button>
          </form>
        )}
      </div>
      {closing && (
        <Modal title="Concluir chamado?" close={() => setClosing(false)}>
          <p>A conversa será excluída permanentemente.</p>
          <div className="actions">
            <Button className="secondary" onClick={() => setClosing(false)}>
              Cancelar
            </Button>
            <Button
              className="primary"
              busy={busy}
              onClick={() =>
                run(async () => {
                  await api(`/tickets/${selected.id}`, undefined, "DELETE");
                  setClosing(false);
                  setId(null);
                  await load();
                })
              }
            >
              Concluir e excluir
            </Button>
          </div>
        </Modal>
      )}
    </div>
  );
}
