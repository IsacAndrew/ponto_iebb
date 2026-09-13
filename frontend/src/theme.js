const key = "ponto-theme";

export function applyTheme(theme) {
  document.documentElement.dataset.theme = theme === "dark" ? "dark" : "light";
}

export function setTheme(theme) {
  applyTheme(theme);
  try {
    localStorage.setItem(key, theme);
  } catch {
    // The theme still works when browser storage is unavailable.
  }
}

let saved = "light";
try {
  saved = localStorage.getItem(key) || "light";
} catch {}
applyTheme(saved);

window.addEventListener("storage", (event) => {
  if (event.key === key || event.key === null) applyTheme(event.newValue);
});
