import { useQuery } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";

import { api, chamar, type Esquemas } from "../api/client";
import { useAcao } from "../api/mutacao";
import { Alternador, Campo, Cartao, Estado, Titulo } from "../components/ui";
import { formatarData } from "../formatos";

type Usuario = Esquemas["UsuarioResponse"];
type Perfil = Esquemas["UsuarioCreate"]["perfil"] & string;

const PERFIS: { valor: Perfil; nome: string; descricao: string }[] = [
  { valor: "admin", nome: "Admin", descricao: "tudo, inclusive gerenciar usuários" },
  { valor: "operador", nome: "Operador", descricao: "usa o painel, sem gerenciar usuários" },
];

const SENHA_MINIMA = 8;

export function Usuarios() {
  const usuarios = useQuery({ queryKey: ["usuarios"], queryFn: () => chamar(api.GET("/usuarios")) });
  const eu = useQuery({ queryKey: ["eu"], queryFn: () => chamar(api.GET("/auth/eu")) });
  const [criando, setCriando] = useState(false);
  const [redefinindo, setRedefinindo] = useState<Usuario | null>(null);

  const atualizar = useAcao(
    ({ id, dados }: { id: number; dados: Esquemas["UsuarioUpdate"] }) =>
      chamar(api.PATCH("/usuarios/{usuario_id}", { params: { path: { usuario_id: id } }, body: dados })),
    { sucesso: "Usuário atualizado.", recarregar: [["usuarios"]] },
  );

  return (
    <>
      <Titulo
        titulo="Usuários"
        descricao="Quem pode entrar no painel. Admin gerencia tudo; operador usa o painel sem gerenciar usuários."
        acoes={
          <button className="botao botao-principal" onClick={() => setCriando((v) => !v)}>
            {criando ? "Fechar" : "Novo usuário"}
          </button>
        }
      />

      {criando && <NovoUsuario aoCriar={() => setCriando(false)} />}
      {redefinindo && <RedefinirSenha usuario={redefinindo} aoFechar={() => setRedefinindo(null)} />}

      <Cartao>
        <Estado carregando={usuarios.isLoading} erro={usuarios.error} vazio={usuarios.data?.length === 0 && "Nenhum usuário."} />
        {usuarios.data && usuarios.data.length > 0 && (
          <div className="tabela-rolagem">
            <table>
              <thead>
                <tr>
                  <th>Nome</th>
                  <th>Login</th>
                  <th>Perfil</th>
                  <th>Situação</th>
                  <th>Último acesso</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {usuarios.data.map((usuario) => {
                  const souEu = usuario.id === eu.data?.id;
                  return (
                    <tr key={usuario.id}>
                      <td>
                        <strong>{usuario.nome}</strong>
                        {souEu && <span className="detalhe"> · você</span>}
                      </td>
                      <td>
                        <code>{usuario.login}</code>
                      </td>
                      <td>
                        <select
                          className="selecao-pequena"
                          value={usuario.perfil}
                          disabled={souEu || atualizar.isPending}
                          title={souEu ? "Você não pode mudar o próprio perfil" : undefined}
                          onChange={(e) => atualizar.mutate({ id: usuario.id, dados: { perfil: e.target.value as Perfil } })}
                        >
                          {PERFIS.map((p) => (
                            <option key={p.valor} value={p.valor}>
                              {p.nome}
                            </option>
                          ))}
                        </select>
                      </td>
                      <td>
                        <Alternador
                          rotulo={usuario.ativo ? "Ativo" : "Inativo"}
                          ligado={usuario.ativo}
                          desabilitado={souEu || atualizar.isPending}
                          aoMudar={(ativo) => atualizar.mutate({ id: usuario.id, dados: { ativo } })}
                        />
                      </td>
                      <td>{usuario.ultimo_login_em ? formatarData(usuario.ultimo_login_em) : "nunca"}</td>
                      <td className="acoes">
                        {!souEu && (
                          <button className="botao" onClick={() => setRedefinindo(usuario)}>
                            Redefinir senha
                          </button>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
        <p className="detalhe">
          Desativar um usuário ou redefinir a senha dele encerra as sessões abertas. Sempre sobra ao menos um admin
          ativo. A sua própria senha se troca em <Link to="/conta">Minha conta</Link>.
        </p>
      </Cartao>
    </>
  );
}

function NovoUsuario({ aoCriar }: { aoCriar: () => void }) {
  const [form, setForm] = useState({ nome: "", login: "", senha: "", confirmacao: "", perfil: "operador" as Perfil });
  const mudar = (campo: keyof typeof form, valor: string) => setForm((f) => ({ ...f, [campo]: valor }));
  const senhasDiferentes = form.confirmacao !== "" && form.senha !== form.confirmacao;

  const criar = useAcao(
    () =>
      chamar(
        api.POST("/usuarios", {
          body: { nome: form.nome, login: form.login, senha: form.senha, perfil: form.perfil },
        }),
      ),
    { sucesso: (u) => `Usuário ${u.login} criado.`, recarregar: [["usuarios"]] },
  );

  return (
    <Cartao titulo="Novo usuário">
      <form
        className="formulario grade-formulario"
        onSubmit={(e: FormEvent) => {
          e.preventDefault();
          if (!senhasDiferentes) criar.mutate(undefined, { onSuccess: aoCriar });
        }}
      >
        <Campo rotulo="Nome">
          <input required maxLength={120} value={form.nome} onChange={(e) => mudar("nome", e.target.value)} />
        </Campo>
        <Campo rotulo="Login" dica="Letras, números, ponto, hífen ou sublinhado.">
          <input
            required
            minLength={3}
            maxLength={60}
            pattern="[A-Za-z0-9._\-]+"
            autoComplete="off"
            value={form.login}
            onChange={(e) => mudar("login", e.target.value)}
          />
        </Campo>
        <Campo rotulo="Perfil" dica={PERFIS.find((p) => p.valor === form.perfil)?.descricao}>
          <select value={form.perfil} onChange={(e) => mudar("perfil", e.target.value)}>
            {PERFIS.map((p) => (
              <option key={p.valor} value={p.valor}>
                {p.nome}
              </option>
            ))}
          </select>
        </Campo>
        <Campo rotulo="Senha" dica={`Mínimo de ${SENHA_MINIMA} caracteres.`}>
          <input
            required
            type="password"
            minLength={SENHA_MINIMA}
            autoComplete="new-password"
            value={form.senha}
            onChange={(e) => mudar("senha", e.target.value)}
          />
        </Campo>
        <Campo rotulo="Repita a senha" dica={senhasDiferentes ? "As senhas não conferem." : undefined}>
          <input
            required
            type="password"
            autoComplete="new-password"
            value={form.confirmacao}
            onChange={(e) => mudar("confirmacao", e.target.value)}
          />
        </Campo>
        <div className="campo-largo">
          <button className="botao botao-principal" disabled={criar.isPending || senhasDiferentes}>
            Criar usuário
          </button>
        </div>
      </form>
    </Cartao>
  );
}

function RedefinirSenha({ usuario, aoFechar }: { usuario: Usuario; aoFechar: () => void }) {
  const [senha, setSenha] = useState("");

  const redefinir = useAcao(
    () => chamar(api.PUT("/usuarios/{usuario_id}/senha", { params: { path: { usuario_id: usuario.id } }, body: { senha } })),
    { sucesso: `Senha de ${usuario.login} redefinida. Passe a nova senha para a pessoa.` },
  );

  return (
    <Cartao
      titulo={`Redefinir a senha de ${usuario.nome}`}
      acoes={
        <button className="botao botao-texto" onClick={aoFechar}>
          Cancelar
        </button>
      }
    >
      <form
        className="formulario-linha"
        onSubmit={(e) => {
          e.preventDefault();
          redefinir.mutate(undefined, { onSuccess: aoFechar });
        }}
      >
        <Campo rotulo="Nova senha">
          <input
            required
            autoFocus
            type="password"
            minLength={SENHA_MINIMA}
            autoComplete="new-password"
            value={senha}
            onChange={(e) => setSenha(e.target.value)}
          />
        </Campo>
        <button className="botao botao-principal" disabled={redefinir.isPending}>
          Redefinir
        </button>
      </form>
      <p className="detalhe">As sessões abertas de {usuario.login} serão encerradas.</p>
    </Cartao>
  );
}
