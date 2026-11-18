import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { NavLink, Navigate, Route, Routes, useLocation, useNavigate } from "react-router-dom";

import { api, chamar } from "./api/client";
import { encerrarSessao, obterToken } from "./api/sessao";

import { Automacoes } from "./pages/Automacoes";
import { Categorias } from "./pages/Categorias";
import { Grupos } from "./pages/Grupos";
import { Integracoes } from "./pages/Integracoes";
import { Login } from "./pages/Login";
import { MinhaConta } from "./pages/MinhaConta";
import { Painel } from "./pages/Painel";
import { Produtos } from "./pages/Produtos";
import { Publicacoes } from "./pages/Publicacoes";
import { Usuarios } from "./pages/Usuarios";

type ItemMenu = { caminho: string; nome: string; tela: JSX.Element; soAdmin?: boolean };

const MENU: ItemMenu[] = [
  { caminho: "/", nome: "Painel", tela: <Painel /> },
  { caminho: "/produtos", nome: "Produtos", tela: <Produtos /> },
  { caminho: "/publicacoes", nome: "Publicações", tela: <Publicacoes /> },
  { caminho: "/categorias", nome: "Categorias", tela: <Categorias /> },
  { caminho: "/grupos", nome: "Grupos", tela: <Grupos /> },
  { caminho: "/automacoes", nome: "Automações", tela: <Automacoes /> },
  { caminho: "/integracoes", nome: "Lojas e canais", tela: <Integracoes /> },
  { caminho: "/usuarios", nome: "Usuários", tela: <Usuarios />, soAdmin: true },
];

export function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="*" element={<AreaLogada />} />
    </Routes>
  );
}

function AreaLogada() {
  const local = useLocation();
  if (!obterToken()) {
    return <Navigate to={`/login?voltar=${encodeURIComponent(local.pathname)}`} replace />;
  }
  return <Layout />;
}

function Layout() {
  const [menuAberto, setMenuAberto] = useState(false);
  const navegar = useNavigate();
  const clienteQuery = useQueryClient();
  const eu = useQuery({ queryKey: ["eu"], queryFn: () => chamar(api.GET("/auth/eu")), staleTime: 60_000 });

  // Telas de admin só aparecem para admin (a API também recusa com 403).
  const itens = MENU.filter((item) => !item.soAdmin || eu.data?.perfil === "admin");

  function sair() {
    encerrarSessao();
    clienteQuery.clear();
    navegar("/login", { replace: true });
  }

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
          {itens.map((item) => (
            <NavLink key={item.caminho} to={item.caminho} end={item.caminho === "/"} onClick={() => setMenuAberto(false)}>
              {item.nome}
            </NavLink>
          ))}
        </nav>
        <div className="menu-rodape">
          {eu.data && (
            <NavLink to="/conta" className="menu-conta" onClick={() => setMenuAberto(false)} title="Minha conta">
              <strong>{eu.data.nome}</strong> · {eu.data.perfil}
            </NavLink>
          )}
          <button className="botao botao-texto" onClick={sair}>
            Sair
          </button>
          <p>v0.9.0</p>
        </div>
      </aside>

      <button className="botao-menu" aria-label="Abrir menu" onClick={() => setMenuAberto((v) => !v)}>
        ☰
      </button>

      <main className="conteudo">
        <Routes>
          {itens.map((item) => (
            <Route key={item.caminho} path={item.caminho} element={item.tela} />
          ))}
          <Route path="/conta" element={<MinhaConta />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  );
}
