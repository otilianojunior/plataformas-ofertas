import { useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { Navigate, useNavigate, useSearchParams } from "react-router-dom";

import { api, chamar } from "../api/client";
import { obterToken, salvarToken } from "../api/sessao";
import { Campo, textoDoErro } from "../components/ui";

export function Login() {
  const navegar = useNavigate();
  const clienteQuery = useQueryClient();
  const [parametros] = useSearchParams();
  const [login, setLogin] = useState("");
  const [senha, setSenha] = useState("");
  const [erro, setErro] = useState<string | null>(null);
  const [entrando, setEntrando] = useState(false);

  // Só caminhos internos, para o ?voltar= não levar a outro site.
  const voltar = parametros.get("voltar");
  const destino = voltar && voltar.startsWith("/") && !voltar.startsWith("//") && !voltar.startsWith("/login") ? voltar : "/";

  if (obterToken()) return <Navigate to={destino} replace />;

  async function entrar(e: FormEvent) {
    e.preventDefault();
    setErro(null);
    setEntrando(true);
    try {
      const sessao = await chamar(api.POST("/auth/login", { body: { login, senha } }));
      salvarToken(sessao.access_token);
      clienteQuery.clear();
      navegar(destino, { replace: true });
    } catch (falha) {
      setErro(textoDoErro(falha));
      setSenha("");
    } finally {
      setEntrando(false);
    }
  }

  return (
    <main className="tela-login">
      <form className="cartao formulario cartao-login" onSubmit={entrar}>
        <div className="marca">
          <span className="marca-icone" aria-hidden>
            %
          </span>
          Plataformas de Ofertas
        </div>
        <p className="detalhe">Entre para acessar o painel de administração.</p>
        <Campo rotulo="Login">
          <input required autoFocus autoComplete="username" value={login} onChange={(e) => setLogin(e.target.value)} />
        </Campo>
        <Campo rotulo="Senha">
          <input required type="password" autoComplete="current-password" value={senha} onChange={(e) => setSenha(e.target.value)} />
        </Campo>
        {erro && (
          <p className="erro-texto" role="alert">
            {erro}
          </p>
        )}
        <button className="botao botao-principal" disabled={entrando}>
          {entrando ? "Entrando…" : "Entrar"}
        </button>
      </form>
    </main>
  );
}
