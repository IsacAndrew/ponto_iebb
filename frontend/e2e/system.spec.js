import { test, expect } from "@playwright/test";

for (const role of [
  "Colaborador",
  "Professor",
  "Administração",
  "Diretoria",
  "Suporte",
]) {
  test(`theme: ${role} can switch and retain their preference`, async ({
    page,
    playwright,
    browser,
  }, info) => {
    if (role === "Professor")
      await page.setViewportSize({ width: 390, height: 844 });
    const person = await newPerson(playwright, role);
    await login(page, person.login, "102030");
    await page.getByRole("button", { name: "Abrir meu perfil" }).click();
    const control = page.getByRole("switch", { name: "Dark Mode" });
    await expect(control).not.toBeChecked();
    await control.focus();
    await page.keyboard.press("Space");
    await expect(control).toBeChecked();
    await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
    const otherDevice = await browser.newContext({
      storageState: { cookies: await page.context().cookies(), origins: [] },
    });
    const otherPage = await otherDevice.newPage();
    await otherPage.goto("http://127.0.0.1:5051/");
    await expect(otherPage.locator("html")).toHaveAttribute(
      "data-theme",
      "dark",
    );
    await otherDevice.close();
    await page.reload();
    await page.getByRole("button", { name: "Abrir meu perfil" }).click();
    await expect(control).toBeChecked();
    await page.getByRole("button", { name: "Alterar minha senha" }).click();
    await expect(page.getByLabel("Senha atual")).toBeVisible();
    await expect(page.getByRole("dialog")).toHaveCSS(
      "color",
      "rgb(226, 235, 229)",
    );
    await page.screenshot({
      path: info.outputPath("dark-profile.png"),
      fullPage: true,
    });
    await page.getByRole("button", { name: "Fechar", exact: true }).click();
    await page.screenshot({
      path: info.outputPath("dark-switch.png"),
      fullPage: true,
    });
    await control.click();
    await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
  });
}

async function login(page, user = "suporte", password = "e2e-password") {
  await page.clock.setFixedTime(new Date("2026-09-03T10:10:00Z"));
  await page.goto("/");
  await page.getByLabel("Seu login").fill(user);
  await page.getByLabel("Sua senha", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Entrar na minha conta" }).click();
}
async function newPerson(playwright, role = "Professor") {
  const api = await playwright.request.newContext({
    baseURL: "http://127.0.0.1:5051",
    extraHTTPHeaders: { "X-Ponto": "1" },
  });
  await api.post("/api/login", {
    data: { login: "suporte", password: "e2e-password" },
  });
  const login = "browser-" + crypto.randomUUID().slice(0, 8);
  const response = await api.post("/api/people", {
    data: { name: "Ana Oliveira", login, role, hired: "2026-01-01" },
  });
  expect(response.ok()).toBeTruthy();
  const person = await response.json();
  const schedule = await api.post(`/api/people/${person.id}/schedules`, {
    data: {
      effective: "2026-09-03",
      days: {
        3: [
          ["07:00", "12:00"],
          ["13:00", "17:00"],
        ],
      },
    },
  });
  expect(schedule.ok()).toBeTruthy();
  await api.dispose();
  return person;
}
async function activate(page, person) {
  await login(page, person.login, person.initial_password);
  await expect(page.getByRole("heading", { name: "Olá, Ana." })).toBeVisible();
}

test("desktop: login, all administrative pages, download and no runtime errors", async ({
  page,
}, info) => {
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.setViewportSize({ width: 1440, height: 1000 });
  await login(page);
  await expect(page.getByRole("heading", { name: "Olá, Isac." })).toBeVisible();
  await page.screenshot({
    path: info.outputPath("desktop-ponto.png"),
    fullPage: true,
  });
  for (const name of [
    "Pessoas",
    "Gestão de ponto",
    "Relatórios",
    "Meu histórico",
    "Meu perfil",
    "Solicitações",
    "Atendimentos",
    "Ocorrências",
    "Configurações",
  ]) {
    await page
      .getByRole("navigation")
      .getByRole("button", { name, exact: true })
      .click();
    await expect(page.locator(".page-heading h1")).toHaveText(name);
    await expect(page.getByText("Vamos tentar novamente?")).toHaveCount(0);
  }
  await page
    .getByRole("navigation")
    .getByRole("button", { name: "Relatórios", exact: true })
    .click();
  await page
    .getByRole("button", { name: /Baixar|Exportar/ })
    .first()
    .click();
  const downloadPromise = page.waitForEvent("download");
  await page
    .getByRole("button", { name: /Professores/ })
    .last()
    .click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toMatch(/\.xlsx$/);
  expect(errors).toEqual([]);
});

test("mobile: first access, geolocation, real punch and responsive navigation", async ({
  page,
  context,
  playwright,
}, info) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await context.grantPermissions(["geolocation"]);
  await context.setGeolocation({
    latitude: -23.67637077,
    longitude: -46.76243126,
    accuracy: 10,
  });
  const person = await newPerson(playwright);
  await activate(page, person);
  await page
    .getByRole("button", { name: "Registrar ponto", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "Ponto registrado", exact: true }),
  ).toBeVisible();
  await expect(page.getByText("Em expediente", { exact: true })).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Sua jornada hoje" }),
  ).not.toBeVisible();
  await page.getByText("Consultar registros", { exact: true }).click();
  await expect(
    page.locator(".day-stats").getByText("0h00", { exact: true }),
  ).toBeVisible();
  await page.getByText("Consultar registros", { exact: true }).click();
  await page.screenshot({
    path: info.outputPath("mobile-ponto.png"),
    fullPage: true,
  });
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth > innerWidth,
  );
  expect(overflow).toBeFalsy();
  await page.getByRole("button", { name: "Abrir menu" }).click();
  await page
    .getByRole("navigation")
    .getByRole("button", { name: "Meu histórico" })
    .click();
  await expect(page.locator(".page-heading h1")).toHaveText("Meu histórico");
});

test("admin: default password after creation and reset", async ({ page }) => {
  await login(page);
  await page
    .getByRole("navigation")
    .getByRole("button", { name: "Pessoas", exact: true })
    .click();
  await page.getByRole("button", { name: "Novo usuário" }).click();
  await page.getByLabel("Nome completo").fill("Cadastro de teste");
  await page
    .getByLabel("Login", { exact: true })
    .fill("create-" + crypto.randomUUID().slice(0, 8));
  await page.getByRole("button", { name: "Salvar cadastro" }).click();
  const credential = page.locator(".credential-box code");
  await expect(credential).toBeVisible();
  const first = await credential.textContent();
  await page.getByRole("button", { name: "Acesso", exact: true }).click();
  await page
    .getByRole("button", { name: "Redefinir senha", exact: true })
    .click();
  await page.getByRole("button", { name: "Confirmar", exact: true }).click();
  await expect(credential).toHaveText("102030");
  expect(first).toBe("102030");
});

test("denied geolocation never confirms a punch", async ({
  page,
  playwright,
}) => {
  const person = await newPerson(playwright);
  await page.addInitScript(() => {
    Object.defineProperty(navigator, "geolocation", {
      value: {
        watchPosition: (_ok, fail) => {
          setTimeout(() => fail({ code: 1 }), 0);
          return 1;
        },
        clearWatch: () => {},
      },
    });
  });
  await activate(page, person);
  await page
    .getByRole("button", { name: "Registrar ponto", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Vamos conferir sua localização" }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Ponto registrado", exact: true }),
  ).toHaveCount(0);
});

test("login screen fits a small phone and explains invalid credentials", async ({
  page,
}, info) => {
  await page.setViewportSize({ width: 360, height: 800 });
  await login(page, "missing-user", "wrong-password");
  await expect(page.getByRole("alert")).toContainText(
    "Login ou senha incorretos",
  );
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth > innerWidth,
    ),
  ).toBeFalsy();
  await page.screenshot({
    path: info.outputPath("mobile-login.png"),
    fullPage: true,
  });
});

test("QR page confirms the signed-in person and remains readable", async ({
  page,
  context,
  playwright,
}) => {
  const person = await newPerson(playwright);
  const admin = await playwright.request.newContext({
    baseURL: "http://127.0.0.1:5051",
    extraHTTPHeaders: { "X-Ponto": "1" },
  });
  await admin.post("/api/login", {
    data: { login: "suporte", password: "e2e-password" },
  });
  const qr = await (await admin.post("/api/system/qr", { data: {} })).json();
  await admin.dispose();
  await context.grantPermissions(["geolocation"]);
  await context.setGeolocation({
    latitude: -23.67637077,
    longitude: -46.76243126,
    accuracy: 10,
  });
  await activate(page, person);
  await page.goto(qr.url);
  await page.getByRole("button", { name: "Entrada", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Ana, entrada registrada com sucesso" }),
  ).toBeVisible();
  await expect(
    page.getByRole("link", { name: "Voltar ao meu ponto" }),
  ).toBeVisible();
});

test("calendar is editable and an employee can change their password", async ({
  page,
  playwright,
}) => {
  await login(page);
  await page
    .getByRole("navigation")
    .getByRole("button", { name: "Relatórios", exact: true })
    .click();
  await page.getByRole("button", { name: "Calendário escolar" }).click();
  await page.getByLabel("Data", { exact: true }).fill("2026-09-07");
  await page.getByLabel("Feriado / dia sem expediente").fill("Independência");
  await page.getByRole("button", { name: "Salvar", exact: true }).click();
  await expect(page.getByText("07/09/2026 · Independência")).toBeVisible();
  const person = await newPerson(playwright);
  await activate(page, person);
  await expect(page.getByRole("navigation")).not.toBeVisible();
  await expect(
    page.getByRole("button", { name: "Registrar ponto", exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Abrir menu" }).click();
  await page
    .getByRole("navigation")
    .getByRole("button", { name: "Meu perfil", exact: true })
    .click();
  await page.getByRole("button", { name: "Alterar minha senha" }).click();
  await page.getByLabel("Senha atual").fill("102030");
  await page
    .getByLabel("Nova senha", { exact: true })
    .fill("changed-browser-password");
  await page
    .getByLabel("Confirmar nova senha")
    .fill("changed-browser-password");
  await page.getByRole("button", { name: "Salvar nova senha" }).click();
  await expect(page.getByRole("status")).toContainText("Senha atualizada");
  await page.getByRole("button", { name: "Abrir menu" }).click();
  await page.getByRole("button", { name: "Sair da conta" }).click();
  await login(page, person.login, "changed-browser-password");
  await expect(page.getByRole("heading", { name: "Olá, Ana." })).toBeVisible();
});

test("reset: rejects wrong password and clears test database with autofilled password", async ({
  page,
  playwright,
}) => {
  const person = await newPerson(playwright);
  await login(page);
  await page
    .getByRole("navigation")
    .getByRole("button", { name: "Configurações", exact: true })
    .click();
  await expect(
    page.getByText("Banco local: SQLite", { exact: true }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Gerar dados de teste (+1%)", exact: true })
    .click();
  const regenerate = page.getByRole("button", {
    name: "Recriar dados de teste (+1%)",
    exact: true,
  });
  await expect(regenerate).toBeEnabled();
  const regenerated = page.waitForResponse((r) =>
    r.url().endsWith("/api/system/storage-test"),
  );
  await regenerate.click();
  expect((await regenerated).status()).toBe(200);
  await expect(regenerate).toBeEnabled();
  await page
    .getByRole("button", { name: "Apagar dados do sistema", exact: true })
    .click();
  const dialog = page.getByRole("dialog");
  const password = dialog.getByLabel("Sua senha", { exact: true });
  const submit = dialog.getByRole("button", {
    name: "Apagar dados definitivamente",
  });
  await password.fill("wrong-password");
  await expect(submit).toBeEnabled();
  await dialog.getByLabel("Repita sua senha").fill("different-password");
  await submit.click();
  await expect(dialog.getByRole("alert")).toContainText(
    "As senhas não conferem",
  );
  await dialog.getByLabel("Repita sua senha").fill("wrong-password");
  const denied = page.waitForResponse((r) =>
    r.url().endsWith("/api/system/reset"),
  );
  await submit.click();
  expect((await denied).status()).toBe(403);
  await expect(dialog.getByRole("alert")).toContainText("Senha incorreta");
  // Simulate a password manager updating the DOM without a React change event.
  await password.evaluate((input) => {
    input.value = "e2e-password";
  });
  await dialog.getByLabel("Repita sua senha").evaluate((input) => {
    input.value = "e2e-password";
  });
  const cleared = page.waitForResponse((r) =>
    r.url().endsWith("/api/system/reset"),
  );
  await submit.click();
  expect((await cleared).status()).toBe(200);
  await expect(
    page.getByRole("button", { name: "Entrar na minha conta" }),
  ).toBeVisible();
  await login(page);
  await page
    .getByRole("navigation")
    .getByRole("button", { name: "Pessoas", exact: true })
    .click();
  await expect(page.getByText(person.login, { exact: true })).toHaveCount(0);
  const people = await page.request.get("/api/people");
  const remaining = await people.json();
  expect(remaining).toHaveLength(1);
  expect(remaining[0].login).toBe("suporte");
});
