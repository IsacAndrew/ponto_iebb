import React from "react";
import { createRoot } from "react-dom/client";
import App from "./app";
import { QRAccess } from "./qr";
import "./style.css";
import "./styles/design.css";
class ErrorBoundary extends React.Component {
  state = { failed: false };
  static getDerivedStateFromError() {
    return { failed: true };
  }
  render() {
    return this.state.failed ? (
      <main className="access-shell">
        <section className="login-card">
          <h1>Vamos tentar novamente?</h1>
          <p>
            A tela encontrou um problema. Seus registros já confirmados
            continuam salvos.
          </p>
          <button className="primary" onClick={() => location.reload()}>
            Recarregar página
          </button>
        </section>
      </main>
    ) : (
      this.props.children
    );
  }
}
createRoot(document.getElementById("root")).render(
  <ErrorBoundary>
    {location.pathname.startsWith("/q/") ? <QRAccess /> : <App />}
  </ErrorBoundary>,
);
