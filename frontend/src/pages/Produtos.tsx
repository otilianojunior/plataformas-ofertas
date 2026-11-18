import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";

import { api, chamar, ErroApi, type Esquemas } from "../api/client";
import { useAcao } from "../api/mutacao";
import { Campo, Cartao, Estado, Etiqueta, Titulo } from "../components/ui";
import { formatarData, formatarPercentual, formatarPreco } from "../formatos";

type Produto = Esquemas["ProdutoResponse"];
type ResultadoManual = Esquemas["PublicacaoManualResponse"];

const POR_PAGINA = 50;

export function Produtos() {
  const produtos = useQuery({ queryKey: ["produtos"], queryFn: () => chamar(api.GET("/produtos")) });
  const categorias = useQuery({ queryKey: ["categorias"], queryFn: () => chamar(api.GET("/categorias")) });
  const lojas = useQuery({ queryKey: ["lojas"], queryFn: () => chamar(api.GET("/lojas")) });

  const [busca, setBusca] = useState("");
  const [loja, setLoja] = useState("");
  const [categoria, setCategoria] = useState("");
  const [somenteElegiveis, setSomenteElegiveis] = useState(true);
  const [pagina, setPagina] = useState(0);
  const [resultado, setResultado] = useState<{ titulo: string; dados: ResultadoManual } | null>(null);

  const nomeCategoria = useMemo(() => Object.fromEntries((categorias.data ?? []).map((c) => [c.id, c.nome_categoria])), [categorias.data]);
  const nomeLoja = useMemo(() => Object.fromEntries((lojas.data ?? []).map((l) => [l.id, l.nome])), [lojas.data]);

  const filtrados = useMemo(() => {
    const termo = busca.trim().toLowerCase();
    return (produtos.data ?? [])
      .filter((p) => !somenteElegiveis || p.elegivel_divulgacao)
      .filter((p) => !loja || String(p.plataforma_id) === loja)
      .filter((p) => !categoria || String(p.categoria_id) === categoria)
      .filter((p) => !termo || p.titulo.toLowerCase().includes(termo))
      .sort((a, b) => Number(b.percentual_desconto ?? 0) - Number(a.percentual_desconto ?? 0));
  }, [produtos.data, busca, loja, categoria, somenteElegiveis]);

  const totalPaginas = Math.max(1, Math.ceil(filtrados.length / POR_PAGINA));
  const visiveis = filtrados.slice(pagina * POR_PAGINA, (pagina + 1) * POR_PAGINA);
  const filtrar = <T,>(definir: (v: T) => void) => (v: T) => {
    definir(v);
    setPagina(0);
  };

  const publicar = useAcao(
    async (produto: Produto) => {
      try {
        const dados = await chamar(api.POST("/publicacoes/produtos/{produto_id}", { params: { path: { produto_id: produto.id } } }));
        setResultado({ titulo: produto.titulo, dados });
        return dados;
      } catch (erro) {
        // 409/502 trazem o resultado de cada grupo no detalhe
        const detalhe = erro instanceof ErroApi ? (erro.detalhe as ResultadoManual | undefined) : undefined;
        if (detalhe && typeof detalhe === "object" && "resultados" in detalhe) setResultado({ titulo: produto.titulo, dados: detalhe });
        throw erro;
      }
    },
    { sucesso: (d) => `Publicado em ${d.publicadas} de ${d.total_destinos} grupos.`, recarregar: [["status"]] },
  );

  const monitoramento = useAcao(
    ({ id, status }: { id: number; status: string }) =>
      chamar(api.PATCH("/produtos/{produto_id}/monitoramento", { params: { path: { produto_id: id } }, body: { status_monitoramento: status } })),
    { sucesso: "Monitoramento atualizado.", recarregar: [["produtos"]] },
  );

  return (
    <>
      <Titulo titulo="Produtos" descricao="Produtos coletados, prontos para publicar ou em acompanhamento." />

      {resultado && (
        <Cartao
          titulo={`Publicação manual: ${resultado.dados.publicadas}/${resultado.dados.total_destinos} grupos`}
          acoes={
            <button className="botao botao-texto" onClick={() => setResultado(null)}>
              Fechar
            </button>
          }
        >
          <p className="detalhe">{resultado.titulo}</p>
          <ul className="lista">
            {resultado.dados.resultados.map((r) => (
              <li key={r.destino_id}>
                <Etiqueta status={r.status} />
                <strong>{r.nome_destino}</strong>
                <span className="detalhe capitalizar">{r.codigo_canal}</span>
                {r.motivo && <span className="detalhe">{r.motivo}</span>}
              </li>
            ))}
          </ul>
        </Cartao>
      )}

      <Cartao>
        <div className="filtros">
          <Campo rotulo="Buscar">
            <input value={busca} onChange={(e) => filtrar(setBusca)(e.target.value)} placeholder="Título do produto" />
          </Campo>
          <Campo rotulo="Loja">
            <select value={loja} onChange={(e) => filtrar(setLoja)(e.target.value)}>
              <option value="">Todas</option>
              {lojas.data?.map((l) => (
                <option key={l.id} value={l.id}>
                  {l.nome}
                </option>
              ))}
            </select>
          </Campo>
          <Campo rotulo="Categoria">
            <select value={categoria} onChange={(e) => filtrar(setCategoria)(e.target.value)}>
              <option value="">Todas</option>
              {categorias.data
                ?.filter((c) => !loja || String(c.plataforma_id) === loja)
                .map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.nome_categoria} ({nomeLoja[c.plataforma_id]})
                  </option>
                ))}
            </select>
          </Campo>
          <label className="caixa">
            <input type="checkbox" checked={somenteElegiveis} onChange={(e) => filtrar(setSomenteElegiveis)(e.target.checked)} />
            Só elegíveis para publicar
          </label>
          <span className="detalhe">{filtrados.length} produtos</span>
        </div>

        <Estado carregando={produtos.isLoading} erro={produtos.error} vazio={filtrados.length === 0 && !produtos.isLoading && "Nenhum produto com esses filtros."} />

        {visiveis.length > 0 && (
          <div className="tabela-rolagem">
            <table>
              <thead>
                <tr>
                  <th />
                  <th>Produto</th>
                  <th className="numero">Preço</th>
                  <th className="numero">Desconto</th>
                  <th>Link afiliado</th>
                  <th>Monitoramento</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {visiveis.map((produto) => (
                  <tr key={produto.id}>
                    <td>{produto.imagem_url ? <img className="miniatura" src={produto.imagem_url} alt="" loading="lazy" /> : null}</td>
                    <td className="coluna-titulo">
                      <a href={produto.url} target="_blank" rel="noreferrer">
                        {produto.titulo}
                      </a>
                      <div className="detalhe">
                        {nomeLoja[produto.plataforma_id]} · {produto.categoria_id ? nomeCategoria[produto.categoria_id] : "sem categoria"} · coletado{" "}
                        {formatarData(produto.ultima_coleta_em)}
                      </div>
                    </td>
                    <td className="numero">
                      {formatarPreco(produto.preco_atual)}
                      {produto.preco_original && <div className="detalhe riscado">{formatarPreco(produto.preco_original)}</div>}
                    </td>
                    <td className="numero">{formatarPercentual(produto.percentual_desconto)}</td>
                    <td>
                      <Etiqueta status={produto.status_link_afiliado} />
                      {produto.erro_geracao_link_afiliado && <div className="detalhe erro-texto">{produto.erro_geracao_link_afiliado.slice(0, 80)}</div>}
                    </td>
                    <td>
                      <select
                        className="selecao-pequena"
                        value={produto.status_monitoramento}
                        onChange={(e) => monitoramento.mutate({ id: produto.id, status: e.target.value })}
                      >
                        <option value="ativo">Ativo</option>
                        <option value="pausado">Pausado</option>
                        <option value="encerrado">Encerrado</option>
                      </select>
                    </td>
                    <td className="acoes">
                      <button
                        className="botao"
                        disabled={publicar.isPending || !produto.elegivel_divulgacao}
                        title={produto.elegivel_divulgacao ? "Publica em todos os grupos da categoria" : "Produto não elegível"}
                        onClick={() => confirm(`Publicar agora em todos os grupos da categoria?\n\n${produto.titulo}`) && publicar.mutate(produto)}
                      >
                        {publicar.isPending && publicar.variables?.id === produto.id ? "Publicando…" : "Publicar"}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {totalPaginas > 1 && (
          <div className="paginacao">
            <button className="botao" disabled={pagina === 0} onClick={() => setPagina((p) => p - 1)}>
              Anterior
            </button>
            <span className="detalhe">
              Página {pagina + 1} de {totalPaginas}
            </span>
            <button className="botao" disabled={pagina + 1 >= totalPaginas} onClick={() => setPagina((p) => p + 1)}>
              Próxima
            </button>
          </div>
        )}
      </Cartao>
    </>
  );
}
