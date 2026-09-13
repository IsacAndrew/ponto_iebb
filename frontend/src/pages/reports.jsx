import React, { useState, useEffect } from "react";
import { Download, ChevronRight } from "lucide-react";

import { api, Field, Button, Modal, dateNow, dateLabel } from "../ui";

export function Reports({ run, busy, notify }) {
  const previous = new Date();
  previous.setDate(1);
  previous.setMonth(previous.getMonth() - 1);
  const [month, setMonth] = useState(previous.toISOString().slice(0, 7)),
    [calendar, setCalendar] = useState(false),
    [downloadOptions, setDownloadOptions] = useState(false);
  const download = (kind) =>
    run(async () => {
      const monthly = kind === "monthly";
      const blob = await api(
        monthly ? `/month/${month}/export` : "/reports/teachers",
        monthly ? {} : undefined,
      );
      const url = URL.createObjectURL(blob),
        link = document.createElement("a");
      link.href = url;
      link.download = monthly ? `Ponto_${month}.xlsx` : "Professores.xlsx";
      link.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
      setDownloadOptions(false);
      notify("Excel gerado");
    });
  return (
    <>
      <div className="toolbar">
        <Field
          label="Mês"
          type="month"
          value={month}
          onChange={(e) => setMonth(e.target.value)}
        />
        <Button className="secondary" onClick={() => setCalendar(true)}>
          Calendário escolar
        </Button>
      </div>
      <div className="export-area">
        <section className="export-card sheet">
          <FileIcon />
          <h2>Relatório Mensal de Ponto</h2>
          <Button
            className="primary"
            busy={busy}
            disabled={!month}
            onClick={() => setDownloadOptions(true)}
          >
            <Download size={19} />
            Baixar Excel
          </Button>
        </section>
      </div>
      {downloadOptions && (
        <Modal
          title="O que deseja baixar?"
          close={() => setDownloadOptions(false)}
        >
          <button
            className="list-row"
            disabled={busy}
            onClick={() => download("monthly")}
          >
            Registros Mensais
            <ChevronRight size={18} />
          </button>
          <button
            className="list-row"
            disabled={busy}
            onClick={() => download("teachers")}
          >
            Professores
            <ChevronRight size={18} />
          </button>
        </Modal>
      )}
      {calendar && (
        <Calendar run={run} busy={busy} close={() => setCalendar(false)} />
      )}
    </>
  );
}
function FileIcon() {
  return (
    <div className="export-icon">
      <Download size={30} />
    </div>
  );
}
function Calendar({ run, busy, close }) {
  const [rows, setRows] = useState([]),
    [date, setDate] = useState(dateNow()),
    [name, setName] = useState("");
  const load = async () => setRows(await api("/calendar"));
  useEffect(() => {
    run(load);
  }, []);
  return (
    <Modal title="Calendário sem expediente" close={close}>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          run(async () => {
            await api("/calendar", { date, name });
            setName("");
            await load();
          });
        }}
      >
        <div className="form-grid">
          <Field
            label="Data"
            type="date"
            value={date}
            onChange={(e) => setDate(e.target.value)}
            required
          />
          <Field
            label="Feriado / dia sem expediente"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
          />
        </div>
        <Button className="primary" busy={busy}>
          Salvar
        </Button>
      </form>
      {rows.map((r) => (
        <div className="list-row" key={r.date}>
          <span>
            {dateLabel(r.date)} · {r.name}
          </span>
          <button
            className="text-button"
            onClick={() =>
              run(async () => {
                await api("/calendar", { date: r.date, name: "" });
                await load();
              })
            }
          >
            Remover
          </button>
        </div>
      ))}
    </Modal>
  );
}
