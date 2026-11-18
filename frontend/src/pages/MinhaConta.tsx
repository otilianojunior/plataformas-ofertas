import { useQuery } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";

import { api, chamar } from "../api/client";
import { useAcao } from "../api/mutacao";
import { salvarToken } from "../api/sessao";
import { Campo, Cartao, Estado, Titulo } from "../components/ui";
import { formatarData } from "../formatos";

export function MinhaConta() {
  const eu = useQuery({ queryKey: ["eu"], queryFn: () => chamar(api.GET("/auth/eu")) });
  const [atual, setAtual] = useState("");
  const [nova, setNova] = useState("");
  const [confirmacao, setConfirmacao] = useState("");
  const diferentes = confirmacao !== "" && nova !== confirmacao;

  const trocar = useAcao(
    async () => {
      const sessao = await chamar(api.PUT("/auth/senha", { body: { senha_atual: atual, senha_nova: nova } }));
      salvarToken(sessao.access_token); // as outras sessões caem; esta continua
      return sessao;
    },
    { sucesso: "Senha alterada. As outras sessões foram encerradas." },
  );

  return (
    <>
      <Titulo titulo="Minha conta" />
      <Estado carregando={eu.isLoading} erro={eu.error} />
      {eu.data && (
        <div className="grade-duas">
          <Cartao titulo="Dados">
            <dl className="dados">
              <dt>Nome</dt>
              <dd>{eu.data.nome}</dd>
              <dt>Login</dt>
              <dd>
                <code>{eu.data.login}</code>
              </dd>
              <dt>Perfil</dt>
              <dd className="capitalizar">{eu.data.perfil}</dd>
              <dt>Último acesso</dt>
              <dd>{formatarData(eu.data.ultimo_login_em)}</dd>
            </dl>
          </Cartao>
          <Cartao titulo="Trocar senha">
            <form
              className="formulario"
              onSubmit={(e: FormEvent) => {
                e.preventDefault();
                if (diferentes) return;
                trocar.mutate(undefined, {
                  onSuccess: () => {
                    setAtual("");
                    setNova("");
                    setConfirmacao("");
                  },
                });
              }}
            >
              <Campo rotulo="Senha atual">
                <input required type="password" autoComplete="current-password" value={atual} onChange={(e) => setAtual(e.target.value)} />
              </Campo>
              <Campo rotulo="Nova senha" dica="Mínimo de 8 caracteres.">
                <input required type="password" minLength={8} autoComplete="new-password" value={nova} onChange={(e) => setNova(e.target.value)} />
              </Campo>
              <Campo rotulo="Repita a nova senha" dica={diferentes ? "As senhas não conferem." : undefined}>
                <input required type="password" autoComplete="new-password" value={confirmacao} onChange={(e) => setConfirmacao(e.target.value)} />
              </Campo>
              <button className="botao botao-principal" disabled={trocar.isPending || diferentes}>
                Trocar senha
              </button>
            </form>
          </Cartao>
        </div>
      )}
    </>
  );
}
