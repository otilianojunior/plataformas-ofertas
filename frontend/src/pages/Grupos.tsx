import { useQuery } from "@tanstack/react-query";
import { useEffect, useState, type FormEvent } from "react";

import { api, chamar, ErroApi, type Esquemas } from "../api/client";
import { useAcao } from "../api/mutacao";
import { Alternador, Campo, Cartao, Estado, Titulo } from "../components/ui";

type Grupo = Esquemas["DestinoDivulgacaoResponse"];
type Canal = Esquemas["PlataformaDivulgacaoResponse"];

export function Grupos() {
  const grupos = useQuery({ queryKey: ["grupos"], queryFn: () => chamar(api.GET("/grupos")) });
  const canais = useQuery({ queryKey: ["canais"], queryFn: () => chamar(api.GET("/canais-divulgacao")) });
  const [criando, setCriando] = useState(false);

  const canalPorId = Object.fromEntries((canais.data ?? []).map((c) => [c.id, c]));

  return (
    <>
      <Titulo
        titulo="Grupos"
        descricao="Onde as ofertas são publicadas e as regras de cada grupo."
        acoes={
          <button className="botao botao-principal" onClick={() => setCriando((v) => !v)}>
            {criando ? "Fechar" : "Novo grupo"}
          </button>
        }
      />

      {criando && canais.data && <NovoGrupo canais={canais.data} aoCriar={() => setCriando(false)} />}

      <Estado carregando={grupos.isLoading} erro={grupos.error} vazio={grupos.data?.length === 0 && "Nenhum grupo cadastrado."} />

      {grupos.data?.map((grupo) => <CartaoGrupo key={grupo.id} grupo={grupo} canal={canalPorId[grupo.plataforma_divulgacao_id]} />)}
    </>
  );
}

function CartaoGrupo({ grupo, canal }: { grupo: Grupo; canal?: Canal }) {
  const status = useAcao(
    (ativo: boolean) =>
      chamar(api.PATCH("/grupos/{grupo_id}/status", { params: { path: { grupo_id: grupo.id } }, body: { status_destino: ativo } })),
    { sucesso: "Grupo atualizado.", recarregar: [["grupos"], ["status"]] },
  );

  return (
    <Cartao
      titulo={
        <>
          {grupo.nome_destino} <span className="detalhe capitalizar">· {canal?.nome ?? "?"}</span>
        </>
      }
      acoes={
        <Alternador rotulo={grupo.status_destino ? "Ativo" : "Inativo"} ligado={grupo.status_destino} aoMudar={(v) => status.mutate(v)} />
      }
    >
      <p className="detalhe">
        {canal?.codigo === "whatsapp" ? "Nome do grupo no WhatsApp" : "ID do chat"}: <code>{grupo.identificador_destino}</code>
      </p>
      <ConfiguracaoDoGrupo grupoId={grupo.id} />
    </Cartao>
  );
}

const VAZIA = {
  desconto_minimo_percentual: "0",
  preco_minimo: "",
  preco_maximo: "",
  intervalo_publicacao_minutos: "60",
  identificador_rastreamento: "",
  status_configuracao: true,
};

function ConfiguracaoDoGrupo({ grupoId }: { grupoId: number }) {
  const chave = ["grupo-configuracao", String(grupoId)];
  const caminho = { params: { path: { grupo_id: grupoId } } };

  const configuracao = useQuery({
    queryKey: chave,
    queryFn: async () => {
      try {
        return await chamar(api.GET("/grupos/{grupo_id}/configuracao", caminho));
      } catch (erro) {
        if (erro instanceof ErroApi && erro.status === 404) return null; // ainda não criada
        throw erro;
      }
    },
  });

  const [form, setForm] = useState(VAZIA);

  useEffect(() => {
    const c = configuracao.data;
    if (c) {
      setForm({
        desconto_minimo_percentual: String(Number(c.desconto_minimo_percentual)),
        preco_minimo: c.preco_minimo ?? "",
        preco_maximo: c.preco_maximo ?? "",
        intervalo_publicacao_minutos: String(c.intervalo_publicacao_minutos),
        identificador_rastreamento: c.identificador_rastreamento ?? "",
        status_configuracao: c.status_configuracao,
      });
    }
  }, [configuracao.data]);

  const corpo = () => ({
    desconto_minimo_percentual: Number(form.desconto_minimo_percentual),
    preco_minimo: form.preco_minimo === "" ? null : Number(form.preco_minimo),
    preco_maximo: form.preco_maximo === "" ? null : Number(form.preco_maximo),
    intervalo_publicacao_minutos: Number(form.intervalo_publicacao_minutos),
    identificador_rastreamento: form.identificador_rastreamento || null,
    status_configuracao: form.status_configuracao,
  });

  const salvar = useAcao(
    () =>
      configuracao.data
        ? chamar(api.PATCH("/grupos/{grupo_id}/configuracao", { ...caminho, body: corpo() }))
        : chamar(api.POST("/grupos/{grupo_id}/configuracao", { ...caminho, body: corpo() })),
    { sucesso: "Regras do grupo salvas.", recarregar: [chave, ["status"]] },
  );

  if (configuracao.isLoading || configuracao.error) return <Estado carregando={configuracao.isLoading} erro={configuracao.error} />;

  const mudar = (campo: keyof typeof VAZIA, valor: string | boolean) => setForm((f) => ({ ...f, [campo]: valor }));

  return (
    <form
      className="formulario grade-formulario"
      onSubmit={(e: FormEvent) => {
        e.preventDefault();
        salvar.mutate(undefined);
      }}
    >
      {!configuracao.data && <p className="campo-largo aviso-inline">Este grupo ainda não tem regras: sem elas, não recebe publicações automáticas.</p>}
      <Campo rotulo="Desconto mínimo (%)" dica="Vale o maior entre este e o da categoria.">
        <input type="number" min={0} max={100} step="any" value={form.desconto_minimo_percentual} onChange={(e) => mudar("desconto_minimo_percentual", e.target.value)} />
      </Campo>
      <Campo rotulo="Preço mínimo (R$)">
        <input type="number" min={0} step="0.01" value={form.preco_minimo} onChange={(e) => mudar("preco_minimo", e.target.value)} />
      </Campo>
      <Campo rotulo="Preço máximo (R$)">
        <input type="number" min={0} step="0.01" value={form.preco_maximo} onChange={(e) => mudar("preco_maximo", e.target.value)} />
      </Campo>
      <Campo rotulo="Intervalo entre ciclos (min)">
        <input type="number" min={0} value={form.intervalo_publicacao_minutos} onChange={(e) => mudar("intervalo_publicacao_minutos", e.target.value)} />
      </Campo>
      <div className="campo-largo linha-acoes">
        <Alternador rotulo="Publicação automática neste grupo" ligado={form.status_configuracao} aoMudar={(v) => mudar("status_configuracao", v)} />
        <button className="botao botao-principal" disabled={salvar.isPending}>
          {configuracao.data ? "Salvar regras" : "Criar regras"}
        </button>
      </div>
    </form>
  );
}

function NovoGrupo({ canais, aoCriar }: { canais: Canal[]; aoCriar: () => void }) {
  const [canalId, setCanalId] = useState(canais[0]?.id ?? 0);
  const [identificador, setIdentificador] = useState("");
  const [nome, setNome] = useState("");
  const [credencialId, setCredencialId] = useState("");

  const canal = canais.find((c) => c.id === canalId);
  const ehWhatsapp = canal?.codigo === "whatsapp";

  const credenciais = useQuery({
    queryKey: ["credenciais-divulgacao", canalId],
    queryFn: () => chamar(api.GET("/credenciais-divulgacao", { params: { query: { plataforma_divulgacao_id: canalId } } })),
    enabled: !ehWhatsapp && canalId > 0,
  });

  const criar = useAcao(
    () =>
      chamar(
        api.POST("/grupos", {
          body: {
            plataforma_divulgacao_id: canalId,
            identificador_destino: ehWhatsapp ? nome : identificador,
            nome_destino: nome,
            status_destino: true,
            credencial_divulgacao_id: ehWhatsapp || !credencialId ? null : Number(credencialId),
          },
        }),
      ),
    { sucesso: "Grupo criado. Agora defina as regras dele.", recarregar: [["grupos"]] },
  );

  return (
    <Cartao titulo="Novo grupo">
      <form
        className="formulario grade-formulario"
        onSubmit={(e) => {
          e.preventDefault();
          criar.mutate(undefined, { onSuccess: aoCriar });
        }}
      >
        <Campo rotulo="Canal">
          <select value={canalId} onChange={(e) => setCanalId(Number(e.target.value))}>
            {canais.map((c) => (
              <option key={c.id} value={c.id}>
                {c.nome}
              </option>
            ))}
          </select>
        </Campo>
        <Campo rotulo="Nome do grupo" dica={ehWhatsapp ? "Exatamente como aparece no WhatsApp: é por ele que o grupo é encontrado." : undefined}>
          <input required value={nome} onChange={(e) => setNome(e.target.value)} />
        </Campo>
        {!ehWhatsapp && (
          <>
            <Campo rotulo="ID do chat" dica="Ex.: -1001234567890">
              <input required value={identificador} onChange={(e) => setIdentificador(e.target.value)} />
            </Campo>
            <Campo rotulo="Credencial (bot)">
              <select required value={credencialId} onChange={(e) => setCredencialId(e.target.value)}>
                <option value="">Selecione</option>
                {credenciais.data
                  ?.filter((c) => c.status_credencial === "ativa")
                  .map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.nome_credencial}
                    </option>
                  ))}
              </select>
            </Campo>
          </>
        )}
        {ehWhatsapp && (
          <p className="campo-largo aviso-inline">
            WhatsApp Web é uma integração não oficial: o número pode ser restringido. Antes de ativar, faça
            login com <code>make whatsapp-login</code> e teste com <code>make whatsapp-teste GRUPO="…"</code>.
          </p>
        )}
        <div className="campo-largo">
          <button className="botao botao-principal" disabled={criar.isPending}>
            Criar grupo
          </button>
        </div>
      </form>
    </Cartao>
  );
}
