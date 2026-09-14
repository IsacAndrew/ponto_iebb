import React, { useState, useEffect } from "react";
import {
  ChevronRight,
  Settings,
  QrCode,
  Printer,
  BookOpen,
  ArrowLeft,
} from "lucide-react";

import { api, Field, Password, Button, Modal, Empty, classes } from "../ui";

export function SettingsPage({ run, busy, notify, me }) {
  const [resetOpen, setResetOpen] = useState(false),
    [resetConfirmation, setResetConfirmation] = useState("");
  const [file, setFile] = useState(null),
    [geo, setGeo] = useState(null),
    [storage, setStorage] = useState(null),
    [qr, setQr] = useState(null),
    [teachers, setTeachers] = useState(null);
  useEffect(() => {
    run(async () => setStorage(await api("/system/storage")));
  }, []);
  const saveFavicon = () =>
    run(async () => {
      const content = await new Promise((ok, no) => {
        const reader = new FileReader();
        reader.onload = () => ok(String(reader.result).split(",")[1]);
        reader.onerror = no;
        reader.readAsDataURL(file);
      });
      await api("/favicon", { type: file.type, content }, "PUT");
      notify("Favicon atualizado");
      location.reload();
    });
  const openQr = () =>
    run(async () => {
      let value = await api("/system/qr");
      if (!value.active) value = await api("/system/qr", {});
      setQr(value);
    });
  const printQr = () => {
    const w = window.open("", "_blank", "width=600,height=700");
    if (!w) return;
    w.document.write(
      `<title>QR Code do ponto</title><style>body{text-align:center;font:18px Arial;padding:40px}h1{font-size:22px}img{width:380px}</style><h1>Registrar ponto</h1><img alt="QR Code institucional" src="/api/system/qr/image?t=${Date.now()}">`,
    );
    w.document.close();
    const image = w.document.querySelector("img");
    image.addEventListener("load", () => w.print(), { once: true });
    if (image.complete) w.print();
  };
  return (
    <div className="settings-grid">
      <section className="profile-sheet sheet">
        <h2>Favicon do navegador</h2>
        <p>Use JPG, JPEG ou PNG de até 500 KB.</p>
        <input
          type="file"
          accept="image/png,image/jpeg"
          onChange={(e) => setFile(e.target.files[0])}
        />
        <div className="actions">
          <Button
            className="secondary"
            onClick={() =>
              run(async () => {
                await api("/favicon", undefined, "DELETE");
                location.reload();
              })
            }
          >
            Remover
          </Button>
          <Button
            className="primary"
            disabled={!file}
            busy={busy}
            onClick={saveFavicon}
          >
            Enviar favicon
          </Button>
        </div>
        <hr />
        <h2>Ponto e localização</h2>
        <div className="settings-actions">
          <Button
            className="secondary"
            onClick={() =>
              run(async () => setGeo(await api("/support/settings")))
            }
          >
            <Settings size={18} />
            Localização da escola
          </Button>
          <Button className="secondary" onClick={openQr}>
            <QrCode size={18} />
            QR Code
          </Button>
          <Button
            className="secondary settings-wide"
            onClick={() => run(async () => setTeachers(await api("/people")))}
          >
            <BookOpen size={18} />
            Professores por turma
          </Button>
        </div>
      </section>
      {storage && (
        <section className="storage-card sheet">
          <div
            className="storage-bar"
            role="progressbar"
            aria-label="Armazenamento utilizado"
            aria-valuenow={storage.percent}
            aria-valuemin="0"
            aria-valuemax="100"
          >
            <span style={{ height: `${storage.percent}%` }} />
          </div>
          <div>
            <strong>{storage.percent}%</strong>
            <p>Armazenamento do banco</p>
            <small>
              {(storage.used_bytes / 1048576).toFixed(1)} MB de{" "}
              {(storage.limit_bytes / 1048576).toFixed(0)} MB
            </small>
            {me.role === "Suporte" && (
              <Button
                className="secondary database-reset-button"
                busy={busy}
                disabled={storage.test_data}
                onClick={() =>
                  run(async () => {
                    const result = await api("/system/storage-test", {});
                    setStorage(await api("/system/storage"));
                    notify(
                      `Dados de teste criados: ${(result.created_bytes / 1048576).toFixed(1)} MB`,
                    );
                  })
                }
              >
                {storage.test_data
                  ? "Dados de teste criados"
                  : "Gerar dados de teste (+1%)"}
              </Button>
            )}
            {me.role === "Suporte" && (
              <button
                className="danger-text database-reset-button"
                onClick={() => {
                  setResetConfirmation("");
                  setResetOpen(true);
                }}
              >
                Apagar dados do sistema
              </button>
            )}
          </div>
        </section>
      )}
      {resetOpen && (
        <Modal
          title="Apagar dados do sistema"
          close={() => setResetOpen(false)}
        >
          <form
            onSubmit={(e) => {
              e.preventDefault();
              const fields = new FormData(e.currentTarget);
              const password = String(fields.get("password") || "");
              const confirmation = String(fields.get("confirmation") || "");
              run(async () => {
                await api("/system/reset", {
                  password,
                  confirmation,
                });
                location.reload();
              });
            }}
          >
            <p>
              Serão excluídos os demais usuários, jornadas, grades, marcações,
              chamados, solicitações, histórico e configurações, incluindo os
              usuários e registros da versão antiga. Sua conta de Suporte e sua
              senha serão mantidas. Você entrará novamente após a limpeza.
            </p>
            <p>
              Esta ação não pode ser desfeita. No Supabase, a limpeza libera o
              espaço das tabelas do sistema. O uso total não chega a zero, pois
              o banco mantém sua estrutura interna.
            </p>
            <Password
              label="Sua senha"
              name="password"
              autoComplete="current-password"
              required
            />
            <Field
              label="Digite APAGAR para confirmar"
              name="confirmation"
              value={resetConfirmation}
              onChange={(e) => setResetConfirmation(e.target.value)}
              required
            />
            <Button
              className="primary"
              busy={busy}
              disabled={resetConfirmation !== "APAGAR"}
            >
              Apagar dados definitivamente
            </Button>
          </form>
        </Modal>
      )}
      {geo && (
        <Modal title="Localização da escola" close={() => setGeo(null)}>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              run(async () => {
                await api("/support/settings", geo, "PUT");
                setGeo(null);
                notify("Localização salva");
              });
            }}
          >
            <p>
              Rua Vicenzo Catena, 100, Vila Remo. Confira o ponto central antes
              de liberar o registro real.
            </p>
            <div className="form-grid">
              {[
                ["lat", "Latitude"],
                ["lon", "Longitude"],
                ["accuracy", "Precisão máxima (m)"],
              ].map(([key, label]) => (
                <Field
                  key={key}
                  label={label}
                  type="number"
                  step="any"
                  value={geo[key]}
                  onChange={(e) => setGeo({ ...geo, [key]: e.target.value })}
                  required
                />
              ))}
            </div>
            <a
              href={`https://www.openstreetmap.org/?mlat=${geo.lat}&mlon=${geo.lon}#map=19/${geo.lat}/${geo.lon}`}
              target="_blank"
              rel="noreferrer"
            >
              Conferir no mapa
            </a>
            <label className="check">
              <input
                type="checkbox"
                checked={geo.verified}
                onChange={(e) => setGeo({ ...geo, verified: e.target.checked })}
              />
              Coordenadas conferidas para uso real
            </label>
            <Button className="primary" busy={busy}>
              Salvar configuração
            </Button>
          </form>
        </Modal>
      )}
      {qr && (
        <Modal title="QR Code do ponto" close={() => setQr(null)}>
          <p>
            Este QR Code é único e identifica cada usuário pela sessão aberta no
            celular.
          </p>
          <img
            className="qr-preview"
            src={`/api/system/qr/image?t=${qr.url}`}
            alt="QR Code do ponto"
          />
          <div className="actions">
            <Button
              className="secondary"
              onClick={() =>
                run(async () => setQr(await api("/system/qr", {})))
              }
            >
              Gerar novo
            </Button>
            <Button className="primary" onClick={printQr}>
              <Printer size={18} />
              Imprimir
            </Button>
          </div>
        </Modal>
      )}
      {teachers && (
        <TeacherDirectory people={teachers} close={() => setTeachers(null)} />
      )}
    </div>
  );
}
function TeacherDirectory({ people, close }) {
  const [classroom, setClassroom] = useState(null),
    [teacher, setTeacher] = useState(null);
  const professors = people.filter(
    (person) =>
      person.active && (person.roles || [person.role]).includes("Professor"),
  );
  const classrooms = classes.filter((name) =>
    professors.some(
      (person) => (person.details.subjects_by_class?.[name] || []).length,
    ),
  );
  const classroomTeachers = classroom
    ? professors.filter(
        (person) =>
          (person.details.subjects_by_class?.[classroom] || []).length,
      )
    : [];
  const back = () => (teacher ? setTeacher(null) : setClassroom(null));
  return (
    <Modal
      title={teacher ? teacher.name : classroom || "Professores por turma"}
      close={close}
    >
      {(classroom || teacher) && (
        <button className="text-button directory-back" onClick={back}>
          <ArrowLeft size={17} />
          Voltar
        </button>
      )}
      {!classroom && (
        <section className="directory-table">
          {classrooms.map((name) => (
            <button
              className="list-row"
              key={name}
              onClick={() => setClassroom(name)}
            >
              <strong>{name}</strong>
              <ChevronRight size={18} />
            </button>
          ))}
          {!classrooms.length && (
            <Empty>Nenhuma turma com professores cadastrados.</Empty>
          )}
        </section>
      )}
      {classroom && !teacher && (
        <section className="directory-table">
          {classroomTeachers.map((person) => (
            <button
              className="list-row"
              key={person.id}
              onClick={() => setTeacher(person)}
            >
              <strong>{person.name}</strong>
              <ChevronRight size={18} />
            </button>
          ))}
        </section>
      )}
      {teacher && (
        <section className="subject-list">
          {teacher.details.subjects_by_class[classroom].map((subject) => (
            <span key={subject}>{subject}</span>
          ))}
        </section>
      )}
    </Modal>
  );
}
