import { useQuery } from "@tanstack/react-query";
import { useMemo, useState, type FormEvent } from "react";

import { api, chamar, type Esquemas } from "../api/client";
import { useAcao } from "../api/mutacao";
import { Alternador, Campo, Cartao, Estado, Titulo } from "../components/ui";
import { formatarPercentual } from "../formatos";

type Categoria = Esquemas["CategoriaResponse"];
type Grupo = Esquemas["DestinoDivulgacaoResponse"];

export function Categorias() {
  const categorias = useQuery({ queryKey: ["categorias"], queryFn: () => chamar(api.GET("/categorias")) });
  const lojas = useQuery({ queryKey: ["lojas"], queryFn: () => chamar(api.GET("/lojas")) });
  const grupos = useQuery({ queryKey: ["grupos"], queryFn: () => chamar(api.GET("/grupos")) });

  const [loja, setLoja] = useState("");
  const [busca, setBusca] = useState("");
  const [criando, setCriando] = useState(false);

  const nomeDaLoja = useMemo(
    () => Object.fromEntries((lojas.data ?? []).map((l) => [l.id, l.nome])),
    [lojas.data],
  );

  const filtradas = (categorias.data ?? [])
    .filter((c) => !loja || String(c.plataforma_id) === loja)
    .filter((c) => !busca || `${c.nome_categoria} ${c.termo_busca ?? ""}`.toLowerCase().includes(busca.toLowerCase()))
    .sort((a, b) => a.plataforma_id - b.plataforma_id || a.nome_categoria.localeCompare(b.nome_categoria));

  return (
    <>
      <Titulo
        titulo="Categorias"
        descricao="De onde vêm os produtos e para quais grupos eles vão."
        acoes={
          <button className="botao botao-principal" onClick={() => setCriando((v) => !v)}>
            {criando ? "Fechar" : "Nova categoria"}
          </button>
        }
      />

      {criando && lojas.data && grupos.data && (
        <NovaCategoria lojas={lojas.data} grupos={grupos.data} aoCriar={() => setCriando(false)} />
      )}

      <Cartao>
        <div className="filtros">
          <Campo rotulo="Loja">
            <select value={loja} onChange={(e) => setLoja(e.target.value)}>
              <option value="">Todas</option>
              {lojas.data?.map((l) => (
                <option key={l.id} value={l.id}>
                  {l.nome}
                </option>
              ))}
            </select>
          </Campo>
          <Campo rotulo="Buscar">
            <input value={busca} onChange={(e) => setBusca(e.target.value)} placeholder="Nome ou termo" />
          </Campo>
          <span className="detalhe">{filtradas.length} categorias</span>
        </div>

        <Estado carregando={categorias.isLoading} erro={categorias.error} vazio={filtradas.length === 0 && "Nenhuma categoria."} />

        {filtradas.length > 0 && (
          <div className="tabela-rolagem">
            <table>
              <thead>
                <tr>
                  <th>Ativa</th>
                  <th>Categoria</th>
                  <th>Loja</th>
                  <th>Desconto mín.</th>
                  <th>Etiqueta</th>
                  <th>Grupos</th>
                </tr>
              </thead>
              <tbody>
                {filtradas.map((categoria) => (
                  <LinhaCategoria
                    key={categoria.id}
                    categoria={categoria}
                    loja={nomeDaLoja[categoria.plataforma_id] ?? "?"}
                    todosGrupos={grupos.data ?? []}
                  />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Cartao>
    </>
  );
}

function LinhaCategoria({ categoria, loja, todosGrupos }: { categoria: Categoria; loja: string; todosGrupos: Grupo[] }) {
  const caminho = { params: { path: { categoria_id: categoria.id } } };
  const recarregar = [["categorias"]];

  const status = useAcao(
    (ativa: boolean) => chamar(api.PATCH("/categorias/{categoria_id}/status", { ...caminho, body: { status_categoria: ativa } })),
    { sucesso: "Categoria atualizada.", recarregar },
  );

  const desconto = useAcao(
    (valor: number) =>
      chamar(api.PATCH("/categorias/{categoria_id}/desconto-minimo", { ...caminho, body: { desconto_minimo_percentual: valor } })),
    { sucesso: "Desconto mínimo salvo.", recarregar },
  );

  const etiqueta = useAcao(
    (valor: string) =>
      chamar(api.PATCH("/categorias/{categoria_id}/etiqueta-afiliado", { ...caminho, body: { etiqueta_afiliado: valor || null } })),
    { sucesso: "Etiqueta salva.", recarregar },
  );

  return (
    <tr className={categoria.status_categoria ? "" : "linha-inativa"}>
      <td>
        <Alternador
          rotulo=""
          ligado={categoria.status_categoria}
          desabilitado={status.isPending}
          aoMudar={(ativa) => status.mutate(ativa)}
        />
      </td>
      <td>
        <strong>{categoria.nome_categoria}</strong>
        <div className="detalhe">
          {categoria.id_categoria_plataforma}
          {categoria.termo_busca && <> · busca “{categoria.termo_busca}”</>}
        </div>
      </td>
      <td>{loja}</td>
      <td>
        <EdicaoRapida
          valor={String(Number(categoria.desconto_minimo_percentual))}
          exibir={formatarPercentual(categoria.desconto_minimo_percentual)}
          tipo="number"
          min={10}
          max={100}
          aoSalvar={(v) => desconto.mutate(Number(v))}
        />
      </td>
      <td>
        <EdicaoRapida valor={categoria.etiqueta_afiliado ?? ""} exibir={categoria.etiqueta_afiliado ?? "—"} aoSalvar={(v) => etiqueta.mutate(v)} />
      </td>
      <td>
        <GruposDaCategoria categoriaId={categoria.id} todosGrupos={todosGrupos} />
      </td>
    </tr>
  );
}

function GruposDaCategoria({ categoriaId, todosGrupos }: { categoriaId: number; todosGrupos: Grupo[] }) {
  const chave = ["categoria-grupos", String(categoriaId)];
  const grupos = useQuery({
    queryKey: chave,
    queryFn: () => chamar(api.GET("/categorias/{categoria_id}/grupos", { params: { path: { categoria_id: categoriaId } } })),
  });

  const caminho = (grupoId: number) => ({ params: { path: { categoria_id: categoriaId, grupo_id: grupoId } } });

  const associar = useAcao((grupoId: number) => chamar(api.POST("/categorias/{categoria_id}/grupos/{grupo_id}", caminho(grupoId))), {
    sucesso: "Grupo associado.",
    recarregar: [chave],
  });
  const desassociar = useAcao((grupoId: number) => chamar(api.DELETE("/categorias/{categoria_id}/grupos/{grupo_id}", caminho(grupoId))), {
    sucesso: "Grupo removido da categoria.",
    recarregar: [chave],
  });

  const associados = new Set((grupos.data ?? []).map((g) => g.id));
  const disponiveis = todosGrupos.filter((g) => !associados.has(g.id));

  return (
    <div className="fichas">
      {grupos.data?.map((g) => (
        <span key={g.id} className="ficha">
          {g.nome_destino}
          <button aria-label={`Remover ${g.nome_destino}`} onClick={() => desassociar.mutate(g.id)}>
            ×
          </button>
        </span>
      ))}
      {disponiveis.length > 0 && (
        <select
          className="selecao-pequena"
          value=""
          onChange={(e) => e.target.value && associar.mutate(Number(e.target.value))}
          aria-label="Adicionar grupo"
        >
          <option value="">+ grupo</option>
          {disponiveis.map((g) => (
            <option key={g.id} value={g.id}>
              {g.nome_destino}
            </option>
          ))}
        </select>
      )}
    </div>
  );
}

export function EdicaoRapida({
  valor,
  exibir,
  aoSalvar,
  tipo = "text",
  min,
  max,
}: {
  valor: string;
  exibir: string;
  aoSalvar: (valor: string) => void;
  tipo?: "text" | "number";
  min?: number;
  max?: number;
}) {
  const [editando, setEditando] = useState(false);
  const [rascunho, setRascunho] = useState(valor);

  if (!editando) {
    return (
      <button
        className="botao-editavel"
        title="Clique para editar"
        onClick={() => {
          setRascunho(valor);
          setEditando(true);
        }}
      >
        {exibir}
      </button>
    );
  }

  return (
    <form
      className="edicao-rapida"
      onSubmit={(e) => {
        e.preventDefault();
        aoSalvar(rascunho);
        setEditando(false);
      }}
    >
      <input
        autoFocus
        type={tipo}
        min={min}
        max={max}
        step="any"
        value={rascunho}
        onChange={(e) => setRascunho(e.target.value)}
        onKeyDown={(e) => e.key === "Escape" && setEditando(false)}
      />
      <button className="botao">OK</button>
    </form>
  );
}

function NovaCategoria({
  lojas,
  grupos,
  aoCriar,
}: {
  lojas: Esquemas["PlataformaResponse"][];
  grupos: Grupo[];
  aoCriar: () => void;
}) {
  const [dados, setDados] = useState({
    plataforma_id: lojas[0]?.id ?? 0,
    id_categoria_plataforma: "",
    nome_categoria: "",
    termo_busca: "",
    etiqueta_afiliado: "",
    desconto_minimo_percentual: 20,
    grupos_ids: [] as number[],
  });

  const criar = useAcao(
    () =>
      chamar(
        api.POST("/categorias", {
          body: {
            ...dados,
            status_categoria: true,
            termo_busca: dados.termo_busca || null,
            etiqueta_afiliado: dados.etiqueta_afiliado || null,
          },
        }),
      ),
    { sucesso: "Categoria criada.", recarregar: [["categorias"]] },
  );

  const mudar = <K extends keyof typeof dados>(campo: K, valor: (typeof dados)[K]) => setDados((d) => ({ ...d, [campo]: valor }));

  return (
    <Cartao titulo="Nova categoria">
      <form
        className="formulario grade-formulario"
        onSubmit={(e: FormEvent) => {
          e.preventDefault();
          criar.mutate(undefined, { onSuccess: aoCriar });
        }}
      >
        <Campo rotulo="Loja">
          <select value={dados.plataforma_id} onChange={(e) => mudar("plataforma_id", Number(e.target.value))}>
            {lojas.map((l) => (
              <option key={l.id} value={l.id}>
                {l.nome}
              </option>
            ))}
          </select>
        </Campo>
        <Campo rotulo="Nome" dica="Como aparece no painel e nos logs.">
          <input required value={dados.nome_categoria} onChange={(e) => mudar("nome_categoria", e.target.value)} />
        </Campo>
        <Campo rotulo="ID da categoria na loja" dica="Mercado Livre: MLB1664. Shopee: 100578.">
          <input required value={dados.id_categoria_plataforma} onChange={(e) => mudar("id_categoria_plataforma", e.target.value)} />
        </Campo>
        <Campo rotulo="Termo de busca (opcional)" dica="Ex.: headset razer. Vazio = destaques da categoria.">
          <input value={dados.termo_busca} onChange={(e) => mudar("termo_busca", e.target.value)} />
        </Campo>
        <Campo rotulo="Etiqueta de afiliado">
          <input value={dados.etiqueta_afiliado} onChange={(e) => mudar("etiqueta_afiliado", e.target.value)} />
        </Campo>
        <Campo rotulo="Desconto mínimo (%)">
          <input
            type="number"
            min={10}
            max={100}
            required
            value={dados.desconto_minimo_percentual}
            onChange={(e) => mudar("desconto_minimo_percentual", Number(e.target.value))}
          />
        </Campo>
        <fieldset className="campo campo-largo">
          <legend className="campo-rotulo">Grupos que recebem as ofertas</legend>
          <div className="fichas">
            {grupos.map((g) => (
              <label key={g.id} className="ficha ficha-selecao">
                <input
                  type="checkbox"
                  checked={dados.grupos_ids.includes(g.id)}
                  onChange={(e) =>
                    mudar("grupos_ids", e.target.checked ? [...dados.grupos_ids, g.id] : dados.grupos_ids.filter((id) => id !== g.id))
                  }
                />
                {g.nome_destino}
              </label>
            ))}
          </div>
        </fieldset>
        <div className="campo-largo">
          <button className="botao botao-principal" disabled={criar.isPending}>
            Criar categoria
          </button>
        </div>
      </form>
    </Cartao>
  );
}
