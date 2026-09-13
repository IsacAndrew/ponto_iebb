import React, { useState, useEffect } from "react";
import { Search } from "lucide-react";
import { Attendance } from "../people";
import { api, Button, Empty } from "../ui";

import { Records } from "./records";
export function Management(ctx) {
  const [people, setPeople] = useState([]),
    [search, setSearch] = useState(""),
    [choice, setChoice] = useState(""),
    [pid, setPid] = useState(""),
    [attendance, setAttendance] = useState(false),
    [events, setEvents] = useState([]);
  useEffect(() => {
    ctx.run(async () => {
      setPeople(await api("/people"));
      setEvents(await api("/today-events"));
    });
  }, []);
  const options = people.filter((p) =>
    p.name.toLowerCase().includes(search.toLowerCase()),
  );
  return (
    <>
      {attendance ? (
        <>
          <Button className="secondary" onClick={() => setAttendance(false)}>
            Voltar ao histórico
          </Button>
          <Attendance {...ctx} close={() => setAttendance(false)} />
        </>
      ) : (
        <>
          <div className="management-search">
            <div className="search">
              <Search size={18} />
              <input
                placeholder="Digite o nome"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>
            <select
              aria-label="Selecionar usuário"
              value={choice}
              onChange={(e) => setChoice(e.target.value)}
            >
              <option value="">Selecione uma pessoa</option>
              {options.map((p) => (
                <option value={p.id} key={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
            <Button
              className="primary"
              disabled={!choice}
              onClick={() => setPid(choice)}
            >
              Consultar
            </Button>
            <Button className="secondary" onClick={() => setAttendance(true)}>
              Presença do dia
            </Button>
          </div>
          {pid ? (
            <Records {...ctx} administrative personId={pid} />
          ) : (
            <section className="sheet today-events">
              <h2>Marcações de hoje</h2>
              {events.map((e, i) => (
                <p key={i}>
                  <time>{e.time}</time> — {e.name}
                </p>
              ))}
              {!events.length && <Empty>Nenhuma marcação hoje.</Empty>}
            </section>
          )}
        </>
      )}
    </>
  );
}
