import { useQuery } from "@tanstack/react-query";

import { api, chamar } from "../api/client";
import { useAcao } from "../api/mutacao";
import { Cartao, Estado, Etiqueta, Titulo } from "../components/ui";
import { formatarData, formatarHora } from "../formatos";

const ROTA_COLETA = {
  mercado_livre: "/coletas/mercado-livre",
  shopee: "/coletas/shopee",
} as const;

export function Painel() {
  const status = useQuery({
    queryKey: ["status"],
    queryFn: () => chamar(api.GET("/automacoes/status")),
    refetchInterval: 15_000,
  });

  const alterarGeral = useAcao(
    (ativar: boolean) =>
      chamar(api.POST(ativar ? "/configuracoes-sistema/automacoes/ativar" : "/configuracoes-sistema/automacoes/pausar")),
    { sucesso: (c) => (c.automacoes_ativas ? "Automações ativadas." : "Automações pausadas."), recarregar: [["status"]] },
  );

  const coletar = useAcao(
    (codigo: keyof typeof ROTA_COLETA) => chamar(api.POST(ROTA_COLETA[codigo])),
    {
      sucesso: (e) => `Coleta ${e.status}: ${e.quantidade_processada} produtos processados.`,
      recarregar: [["status"], ["produtos"]],
    },
  );

  const dados = status.data;
  const ativas = dados?.configuracoes_sistema.automacoes_ativas;

  return (
    <>
      <Titulo
        titulo="Painel"
        descricao={dados ? `Atualizado ${formatarData(dados.consultado_em)} · horário de Brasília` : undefined}
        acoes={
          dados && (
            <button
              className={ativas ? "botao botao-perigo" : "botao botao-principal"}
              disabled={alterarGeral.isPending}
              onClick={() => alterarGeral.mutate(!ativas)}
            >
              {ativas ? "Pausar todas as automações" : "Ativar automações"}
            </button>
          )
        }
      />

      <Estado carregando={status.isLoading} erro={status.error} />

      {dados && (
        <>
          <div className="grade-resumo">
            <Cartao titulo="Monitor">
              <Etiqueta status={dados.monitor.status} />
              <p className="detalhe">Último sinal: {formatarData(dados.monitor.ultimo_sinal_em)}</p>
            </Cartao>
            <Cartao titulo="Horário">
              <Etiqueta
                status={dados.horario_permitido ? "ativa" : "fora_da_janela"}
                texto={dados.horario_permitido ? "Dentro da janela" : "Fora da janela"}
              />
              <p className="detalhe">
                {dados.janelas_execucao.filter((j) => j.ativa).length === 0
                  ? "Sem janelas: liberado 24h"
                  : dados.janelas_execucao
                      .filter((j) => j.ativa)
                      .map((j) => `${formatarHora(j.hora_inicio)}–${formatarHora(j.hora_fim)}`)
                      .join(" · ")}
              </p>
            </Cartao>
            <Cartao titulo="Automações">
              <Etiqueta status={ativas ? "ativa" : "pausada"} />
              <p className="detalhe">
                Coleta a cada {dados.configuracoes_sistema.intervalo_coleta_minutos} min · até{" "}
                {dados.configuracoes_sistema.limite_produtos_por_categoria} por categoria
              </p>
            </Cartao>
            <Cartao titulo="WhatsApp">
              <Etiqueta status={dados.publicacao_whatsapp_status} />
              <p className="detalhe">Publicação pelo WhatsApp Web</p>
            </Cartao>
          </div>

          <Cartao titulo="Coletas">
            <div className="tabela-rolagem">
              <table>
                <thead>
                  <tr>
                    <th>Loja</th>
                    <th>Status</th>
                    <th>Última execução</th>
                    <th>Processados</th>
                    <th>Próxima</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {dados.coletas.map((coleta) => (
                    <tr key={coleta.codigo}>
                      <td>{coleta.nome}</td>
                      <td>
                        <Etiqueta status={coleta.status} />
                      </td>
                      <td>
                        <Etiqueta status={coleta.ultima_execucao_status} /> {formatarData(coleta.ultima_execucao_finalizada_em)}
                      </td>
                      <td className="numero">
                        {coleta.quantidade_processada ?? "—"}
                        {coleta.quantidade_ignorada ? <span className="detalhe"> ({coleta.quantidade_ignorada} ignorados)</span> : null}
                      </td>
                      <td>{formatarData(coleta.proxima_execucao_em)}</td>
                      <td className="acoes">
                        <button
                          className="botao"
                          disabled={coletar.isPending || coleta.status === "executando"}
                          onClick={() => coletar.mutate(coleta.codigo as keyof typeof ROTA_COLETA)}
                          title="Coleta manual: não obedece às janelas de horário"
                        >
                          {coletar.isPending && coletar.variables === coleta.codigo ? "Coletando…" : "Coletar agora"}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {dados.coletas.some((c) => c.ultima_execucao_erro) && (
              <details className="detalhes">
                <summary>Avisos da última coleta</summary>
                {dados.coletas
                  .filter((c) => c.ultima_execucao_erro)
                  .map((c) => (
                    <pre key={c.codigo}>
                      {c.nome}: {c.ultima_execucao_erro}
                    </pre>
                  ))}
              </details>
            )}
          </Cartao>

          <Cartao titulo="Grupos">
            <Estado vazio={dados.destinos_publicacao.length === 0 && "Nenhum grupo com configuração de divulgação."} />
            {dados.destinos_publicacao.length > 0 && (
              <div className="tabela-rolagem">
                <table>
                  <thead>
                    <tr>
                      <th>Grupo</th>
                      <th>Canal</th>
                      <th>Status</th>
                      <th>Ciclo atual</th>
                      <th>Última publicação</th>
                      <th>Próximo ciclo</th>
                    </tr>
                  </thead>
                  <tbody>
                    {dados.destinos_publicacao.map((grupo) => (
                      <tr key={grupo.destino_id}>
                        <td>{grupo.nome_destino}</td>
                        <td className="capitalizar">{grupo.codigo_canal}</td>
                        <td>
                          <Etiqueta status={grupo.status} />
                        </td>
                        <td>
                          {grupo.ultimo_ciclo ? (
                            <>
                              <Etiqueta status={grupo.ultimo_ciclo.status} />{" "}
                              <span className="numero">
                                {grupo.ultimo_ciclo.quantidade_publicada}/{grupo.ultimo_ciclo.quantidade_candidatos}
                              </span>
                            </>
                          ) : (
                            "—"
                          )}
                        </td>
                        <td>
                          <Etiqueta status={grupo.ultima_publicacao_status} /> {formatarData(grupo.ultima_publicacao_em)}
                          {grupo.ultima_publicacao_erro && <div className="detalhe erro-texto">{grupo.ultima_publicacao_erro}</div>}
                        </td>
                        <td>{formatarData(grupo.proxima_execucao_em)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Cartao>
        </>
      )}
    </>
  );
}
