import { createContext, useCallback, useContext, useState, type ReactNode } from "react";

import { ErroApi } from "../api/client";
import { rotulo, tomDoStatus } from "../formatos";

// --- avisos (toasts) -----------------------------------------------------------

type Aviso = { id: number; tipo: "ok" | "erro"; texto: string };
const ContextoAvisos = createContext<(tipo: Aviso["tipo"], texto: string) => void>(() => {});

export function ProvedorAvisos({ children }: { children: ReactNode }) {
  const [avisos, setAvisos] = useState<Aviso[]>([]);

  const avisar = useCallback((tipo: Aviso["tipo"], texto: string) => {
    const id = Date.now() + Math.random();
    setAvisos((atuais) => [...atuais, { id, tipo, texto }]);
    setTimeout(() => setAvisos((atuais) => atuais.filter((a) => a.id !== id)), tipo === "erro" ? 8000 : 4000);
  }, []);

  return (
    <ContextoAvisos.Provider value={avisar}>
      {children}
      <div className="avisos" role="status" aria-live="polite">
        {avisos.map((aviso) => (
          <div key={aviso.id} className={`aviso aviso-${aviso.tipo}`}>
            {aviso.texto}
          </div>
        ))}
      </div>
    </ContextoAvisos.Provider>
  );
}

export const useAvisos = () => useContext(ContextoAvisos);

export const textoDoErro = (erro: unknown) =>
  erro instanceof ErroApi ? erro.message : "Erro inesperado.";

// --- blocos visuais ------------------------------------------------------------

export function Etiqueta({ status, texto }: { status: string | null | undefined; texto?: string }) {
  return <span className={`etiqueta tom-${tomDoStatus(status)}`}>{texto ?? rotulo(status)}</span>;
}

export function Cartao({ titulo, acoes, children }: { titulo?: ReactNode; acoes?: ReactNode; children: ReactNode }) {
  return (
    <section className="cartao">
      {(titulo || acoes) && (
        <header className="cartao-topo">
          {titulo && <h2>{titulo}</h2>}
          {acoes && <div className="cartao-acoes">{acoes}</div>}
        </header>
      )}
      {children}
    </section>
  );
}

export function Alternador({
  ligado,
  aoMudar,
  rotulo: texto,
  desabilitado,
}: {
  ligado: boolean;
  aoMudar: (ligado: boolean) => void;
  rotulo: string;
  desabilitado?: boolean;
}) {
  return (
    <label className={`alternador ${desabilitado ? "desabilitado" : ""}`}>
      <input
        type="checkbox"
        checked={ligado}
        disabled={desabilitado}
        onChange={(e) => aoMudar(e.target.checked)}
      />
      <span className="trilho" aria-hidden />
      <span className="alternador-texto">{texto}</span>
    </label>
  );
}

export function Estado({ carregando, erro, vazio }: { carregando?: boolean; erro?: unknown; vazio?: string | false }) {
  if (carregando) return <p className="estado">Carregando…</p>;
  if (erro) return <p className="estado estado-erro">{textoDoErro(erro)}</p>;
  if (vazio) return <p className="estado">{vazio}</p>;
  return null;
}

export function Campo({ rotulo: texto, dica, children }: { rotulo: string; dica?: string; children: ReactNode }) {
  return (
    <label className="campo">
      <span className="campo-rotulo">{texto}</span>
      {children}
      {dica && <span className="campo-dica">{dica}</span>}
    </label>
  );
}

export function Titulo({ titulo, descricao, acoes }: { titulo: string; descricao?: string; acoes?: ReactNode }) {
  return (
    <div className="titulo-pagina">
      <div>
        <h1>{titulo}</h1>
        {descricao && <p>{descricao}</p>}
      </div>
      {acoes && <div className="cartao-acoes">{acoes}</div>}
    </div>
  );
}
