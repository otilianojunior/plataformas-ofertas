import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { api, chamar } from "../api/client";
import { Campo, Cartao, Estado, Etiqueta, Titulo } from "../components/ui";
import { formatarData } from "../formatos";

const STATUS = ["em_andamento", "concluido", "pausado", "interrompido", "falhou"] as const;

export function Publicacoes() {
  const [grupo, setGrupo] = useState("");
  const [status, setStatus] = useState("");
  const [limite, setLimite] = useState(30);

  const grupos = useQuery({ queryKey: ["grupos"], queryFn: () => chamar(api.GET("/grupos")) });
  const ciclos = useQuery({
    queryKey: ["ciclos", grupo, status, limite],
    queryFn: () =>
      chamar(
        api.GET("/ciclos-publicacao", {
          params: {
            query: {
              destino_id: grupo ? Number(grupo) : undefined,
              status: (status || undefined) as (typeof STATUS)[number] | undefined,
              limite,
            },
          },
        }),
      ),
    refetchInterval: 20_000,
  });

  const nomeGrupo = Object.fromEntries((grupos.data ?? []).map((g) => [g.id, g.nome_destino]));

  return (
    <>
      <Titulo titulo="Publicações" descricao="Cada ciclo automático de publicação, por grupo." />
      <Cartao>
        <div className="filtros">
          <Campo rotulo="Grupo">
            <select value={grupo} onChange={(e) => setGrupo(e.target.value)}>
              <option value="">Todos</option>
              {grupos.data?.map((g) => (
                <option key={g.id} value={g.id}>
                  {g.nome_destino}
                </option>
              ))}
            </select>
          </Campo>
          <Campo rotulo="Status">
            <select value={status} onChange={(e) => setStatus(e.target.value)}>
              <option value="">Todos</option>
              {STATUS.map((s) => (
                <option key={s} value={s}>
                  {s.replace("_", " ")}
                </option>
              ))}
            </select>
          </Campo>
          <Campo rotulo="Quantidade">
            <select value={limite} onChange={(e) => setLimite(Number(e.target.value))}>
              {[10, 30, 100].map((n) => (
                <option key={n} value={n}>
                  {n}
                </option>
              ))}
            </select>
          </Campo>
        </div>

        <Estado carregando={ciclos.isLoading} erro={ciclos.error} vazio={ciclos.data?.length === 0 && "Nenhum ciclo encontrado."} />

        {ciclos.data && ciclos.data.length > 0 && (
          <div className="tabela-rolagem">
            <table>
              <thead>
                <tr>
                  <th>Início</th>
                  <th>Grupo</th>
                  <th>Status</th>
                  <th className="numero">Candidatos</th>
                  <th className="numero">Publicados</th>
                  <th className="numero">Falhas</th>
                  <th className="numero">Ignorados</th>
                  <th>Fim</th>
                </tr>
              </thead>
              <tbody>
                {ciclos.data.map((ciclo) => (
                  <tr key={ciclo.id}>
                    <td>{formatarData(ciclo.iniciado_em)}</td>
                    <td>{nomeGrupo[ciclo.destino_divulgacao_id] ?? ciclo.destino_divulgacao_id}</td>
                    <td>
                      <Etiqueta status={ciclo.status} />
                      {ciclo.erro && <div className="detalhe erro-texto">{ciclo.erro}</div>}
                    </td>
                    <td className="numero">{ciclo.quantidade_candidatos}</td>
                    <td className="numero">{ciclo.quantidade_publicada}</td>
                    <td className="numero">{ciclo.quantidade_falha}</td>
                    <td className="numero">{ciclo.quantidade_ignorada}</td>
                    <td>{formatarData(ciclo.finalizado_em)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Cartao>
    </>
  );
}
