import { useQuery } from "@tanstack/react-query";
import { useEffect, useState, type FormEvent } from "react";

import { api, chamar } from "../api/client";
import { useAcao } from "../api/mutacao";
import { Alternador, Campo, Cartao, Estado, Titulo } from "../components/ui";
import { formatarHora } from "../formatos";

const AUTOMACOES = [
  { chave: "coleta_mercado_livre", campo: "coleta_mercado_livre_ativa", nome: "Coleta do Mercado Livre" },
  { chave: "coleta_shopee", campo: "coleta_shopee_ativa", nome: "Coleta da Shopee" },
  { chave: "publicacao_telegram", campo: "publicacao_telegram_ativa", nome: "Publicação no Telegram" },
  { chave: "publicacao_whatsapp", campo: "publicacao_whatsapp_ativa", nome: "Publicação no WhatsApp" },
] as const;

const RECARREGAR = [["configuracoes"], ["status"]];

export function Automacoes() {
  const configuracao = useQuery({
    queryKey: ["configuracoes"],
    queryFn: () => chamar(api.GET("/configuracoes-sistema")),
  });

  const alterarAutomacao = useAcao(
    ({ chave, ativar }: { chave: (typeof AUTOMACOES)[number]["chave"]; ativar: boolean }) =>
      chamar(
        api.POST(
          ativar
            ? "/configuracoes-sistema/automacoes/{automacao}/ativar"
            : "/configuracoes-sistema/automacoes/{automacao}/pausar",
          { params: { path: { automacao: chave } } },
        ),
      ),
    { sucesso: "Automação atualizada.", recarregar: RECARREGAR },
  );

  const alterarGeral = useAcao(
    (ativar: boolean) =>
      chamar(api.POST(ativar ? "/configuracoes-sistema/automacoes/ativar" : "/configuracoes-sistema/automacoes/pausar")),
    { sucesso: "Chave geral atualizada.", recarregar: RECARREGAR },
  );

  const [intervalo, setIntervalo] = useState("");
  const [limite, setLimite] = useState("");
  const [limiteCiclo, setLimiteCiclo] = useState("");

  useEffect(() => {
    if (configuracao.data) {
      setIntervalo(String(configuracao.data.intervalo_coleta_minutos));
      setLimite(String(configuracao.data.limite_produtos_por_categoria));
      setLimiteCiclo(String(configuracao.data.limite_publicacoes_por_ciclo));
    }
  }, [configuracao.data]);

  const salvar = useAcao(
    () =>
      chamar(
        api.PATCH("/configuracoes-sistema", {
          body: {
            intervalo_coleta_minutos: Number(intervalo),
            limite_produtos_por_categoria: Number(limite),
            limite_publicacoes_por_ciclo: Number(limiteCiclo),
          },
        }),
      ),
    { sucesso: "Configurações salvas.", recarregar: RECARREGAR },
  );

  const dados = configuracao.data;

  return (
    <>
      <Titulo titulo="Automações" descricao="O que roda sozinho, com que frequência e em quais horários." />
      <Estado carregando={configuracao.isLoading} erro={configuracao.error} />

      {dados && (
        <div className="grade-duas">
          <Cartao titulo="Ligar e desligar">
            <Alternador
              rotulo="Chave geral (todas as automações)"
              ligado={dados.automacoes_ativas}
              desabilitado={alterarGeral.isPending}
              aoMudar={(ligado) => alterarGeral.mutate(ligado)}
            />
            <hr />
            {AUTOMACOES.map((automacao) => (
              <Alternador
                key={automacao.chave}
                rotulo={automacao.nome}
                ligado={dados[automacao.campo]}
                desabilitado={alterarAutomacao.isPending || !dados.automacoes_ativas}
                aoMudar={(ativar) => alterarAutomacao.mutate({ chave: automacao.chave, ativar })}
              />
            ))}
            {!dados.automacoes_ativas && <p className="detalhe">Com a chave geral desligada, nada roda.</p>}
          </Cartao>

          <Cartao titulo="Frequência e limites">
            <form
              className="formulario"
              onSubmit={(e: FormEvent) => {
                e.preventDefault();
                salvar.mutate(undefined);
              }}
            >
              <Campo rotulo="Intervalo entre coletas (minutos)">
                <input type="number" min={1} required value={intervalo} onChange={(e) => setIntervalo(e.target.value)} />
              </Campo>
              <Campo
                rotulo="Produtos por categoria em cada ciclo"
                dica="Vale para cada categoria de cada loja, em todos os grupos."
              >
                <input type="number" min={1} required value={limite} onChange={(e) => setLimite(e.target.value)} />
              </Campo>
              <Campo
                rotulo="Total de publicações por ciclo (em cada grupo)"
                dica="Teto somando todas as categorias. As categorias se revezam: as publicadas há mais tempo vão primeiro."
              >
                <input type="number" min={1} required value={limiteCiclo} onChange={(e) => setLimiteCiclo(e.target.value)} />
              </Campo>
              <button className="botao botao-principal" disabled={salvar.isPending}>
                Salvar
              </button>
            </form>
          </Cartao>
        </div>
      )}

      <Janelas />
    </>
  );
}

function Janelas() {
  const janelas = useQuery({
    queryKey: ["janelas"],
    queryFn: () => chamar(api.GET("/janelas-execucao")),
  });

  const [inicio, setInicio] = useState("08:00");
  const [fim, setFim] = useState("22:00");
  const recarregar = [["janelas"], ["status"]];

  const criar = useAcao(
    () => chamar(api.POST("/janelas-execucao", { body: { hora_inicio: inicio, hora_fim: fim, ativa: true } })),
    { sucesso: "Janela criada.", recarregar },
  );

  const alternar = useAcao(
    ({ id, ativa }: { id: number; ativa: boolean }) =>
      chamar(api.PATCH("/janelas-execucao/{janela_id}", { params: { path: { janela_id: id } }, body: { ativa } })),
    { sucesso: "Janela atualizada.", recarregar },
  );

  const excluir = useAcao(
    (id: number) => chamar(api.DELETE("/janelas-execucao/{janela_id}", { params: { path: { janela_id: id } } })),
    { sucesso: "Janela excluída.", recarregar },
  );

  return (
    <Cartao titulo="Janelas de horário">
      <p className="detalhe">
        Com janelas ativas, coletas e publicações automáticas só rodam dentro delas (horário de Brasília). Sem
        nenhuma, rodam 24h. O fim não conta: para ir até o fim do dia use 23:59:59.
      </p>
      <Estado carregando={janelas.isLoading} erro={janelas.error} vazio={janelas.data?.length === 0 && "Nenhuma janela: liberado 24h."} />
      {janelas.data && janelas.data.length > 0 && (
        <ul className="lista">
          {janelas.data.map((janela) => (
            <li key={janela.id}>
              <strong className="numero">
                {formatarHora(janela.hora_inicio)} – {formatarHora(janela.hora_fim)}
              </strong>
              <Alternador
                rotulo={janela.ativa ? "Ativa" : "Inativa"}
                ligado={janela.ativa}
                aoMudar={(ativa) => alternar.mutate({ id: janela.id, ativa })}
              />
              <button
                className="botao botao-texto"
                onClick={() => confirm("Excluir esta janela?") && excluir.mutate(janela.id)}
              >
                Excluir
              </button>
            </li>
          ))}
        </ul>
      )}
      <form
        className="formulario-linha"
        onSubmit={(e) => {
          e.preventDefault();
          criar.mutate(undefined);
        }}
      >
        <Campo rotulo="Início">
          <input type="time" step={1} required value={inicio} onChange={(e) => setInicio(e.target.value)} />
        </Campo>
        <Campo rotulo="Fim">
          <input type="time" step={1} required value={fim} onChange={(e) => setFim(e.target.value)} />
        </Campo>
        <button className="botao botao-principal" disabled={criar.isPending}>
          Adicionar janela
        </button>
      </form>
    </Cartao>
  );
}
