"use client";
import { useEffect, useState } from "react";
import { getSystemStatus, type SystemStatus } from "../lib/api";

export function SystemStatusPanel() {
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    let active = true;
    getSystemStatus(controller.signal).then((value) => {
      if (active) setStatus(value);
    });
    return () => {
      active = false;
      controller.abort();
    };
  }, [attempt]);
  return (
    <section className="status-card" aria-labelledby="status-heading">
      <div className="section-label">ENGINEERING FOUNDATION · FASE 0</div>
      <h2 id="status-heading">Status do sistema</h2>
      <div role="status" aria-live="polite">
        {!status && <p>Consultando API e banco de dados…</p>}
        {status?.kind === "healthy" && (
          <dl className="status-list">
            <div>
              <dt>API</dt>
              <dd>
                <span className="dot" />
                Operacional
              </dd>
            </div>
            <div>
              <dt>Banco de dados</dt>
              <dd>Pronto</dd>
            </div>
            <div>
              <dt>Build</dt>
              <dd>{status.version.version}</dd>
            </div>
            <div>
              <dt>Ambiente</dt>
              <dd>{status.version.environment}</dd>
            </div>
          </dl>
        )}
        {status && status.kind !== "healthy" && (
          <p className="status-error">{status.message}</p>
        )}
      </div>
      <button
        onClick={() => {
          setStatus(null);
          setAttempt((v) => v + 1);
        }}
      >
        Atualizar status
      </button>
    </section>
  );
}
