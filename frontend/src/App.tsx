import { useState } from "react";
import { NavLink, Navigate, Route, Routes } from "react-router-dom";

import { Automacoes } from "./pages/Automacoes";
import { Categorias } from "./pages/Categorias";
import { Grupos } from "./pages/Grupos";
import { Integracoes } from "./pages/Integracoes";
import { Painel } from "./pages/Painel";
import { Produtos } from "./pages/Produtos";
import { Publicacoes } from "./pages/Publicacoes";

const MENU = [
  { caminho: "/", nome: "Painel", tela: <Painel /> },
  { caminho: "/produtos", nome: "Produtos", tela: <Produtos /> },
  { caminho: "/publicacoes", nome: "Publicações", tela: <Publicacoes /> },
  { caminho: "/categorias", nome: "Categorias", tela: <Categorias /> },
  { caminho: "/grupos", nome: "Grupos", tela: <Grupos /> },
  { caminho: "/automacoes", nome: "Automações", tela: <Automacoes /> },
  { caminho: "/integracoes", nome: "Lojas e canais", tela: <Integracoes /> },
];

export function App() {
  const [menuAberto, setMenuAberto] = useState(false);

  return (
    <div className="aplicacao">
      <aside className={`menu ${menuAberto ? "aberto" : ""}`}>
        <div className="marca">
          <span className="marca-icone" aria-hidden>
            %
          </span>
          Plataformas de Ofertas
        </div>
        <nav>
          {MENU.map((item) => (
            <NavLink key={item.caminho} to={item.caminho} end={item.caminho === "/"} onClick={() => setMenuAberto(false)}>
              {item.nome}
            </NavLink>
          ))}
        </nav>
        <p className="menu-rodape">v0.9.0 · acesso local</p>
      </aside>

      <button className="botao-menu" aria-label="Abrir menu" onClick={() => setMenuAberto((v) => !v)}>
        ☰
      </button>

      <main className="conteudo">
        <Routes>
          {MENU.map((item) => (
            <Route key={item.caminho} path={item.caminho} element={item.tela} />
          ))}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  );
}
