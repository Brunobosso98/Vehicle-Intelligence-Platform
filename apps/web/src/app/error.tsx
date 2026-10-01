"use client";
export default function ErrorBoundary({ reset }: { reset: () => void }) {
  return (
    <main>
      <h1>Não foi possível carregar esta página.</h1>
      <p>Ocorreu um erro inesperado.</p>
      <button onClick={reset}>Tentar novamente</button>
    </main>
  );
}
