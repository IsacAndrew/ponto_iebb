export function applyTheme(theme) {
  document.documentElement.dataset.theme = theme === "dark" ? "dark" : "light";
}

// The authenticated account owns the theme, not the previous browser user.
applyTheme("light");
