import Link from "next/link";
import { SystemStatusPanel } from "../components/system-status";
export default function Home() {
  return (
    <>
      <a className="skip-link" href="#main">
        Pular para o conteúdo
      </a>
      <header>
        <Link
          href="/"
          className="wordmark"
          aria-label="N55 Intelligence Lab início"
        >
          N55<span> / INTELLIGENCE LAB</span>
        </Link>
        <span className="phase">FASE 0</span>
      </header>
      <main id="main">
        <div className="eyebrow">VEHICLE INTELLIGENCE PLATFORM</div>
        <h1>
          Engenharia guiada
          <br />
          por evidências.
        </h1>
        <p className="intro">
          Uma plataforma para observar, compreender e comparar o comportamento
          de veículos. A jornada começa com o BMW N55.
        </p>
        <SystemStatusPanel />
        <section className="scope" aria-labelledby="scope-heading">
          <h2 id="scope-heading">O ponto de partida</h2>
          <p>
            A fundação conecta aplicação, API e banco de dados. Telemetria,
            análises e inteligência veicular serão adicionadas nas próximas
            fases.
          </p>
        </section>
      </main>
      <footer>
        <span>N55 INTELLIGENCE LAB</span>
        <p>
          Observação e análise. Nenhum controle de sistemas críticos do veículo.
        </p>
      </footer>
    </>
  );
}
