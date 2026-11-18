import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { api, chamar } from "../api/client";
import { useAcao } from "../api/mutacao";
import { Alternador, Campo, Cartao, Estado, Etiqueta, Titulo } from "../components/ui";
import { formatarData } from "../formatos";

const URL_API = import.meta.env.DEV ? "/api" : "";

export function Integracoes() {
  return (
    <>
      <Titulo titulo="Lojas e canais" descricao="De onde vêm as ofertas, para onde vão e as credenciais de cada um." />
      <div className="grade-duas">
        <Lojas />
        <Canais />
      </div>
      <CredenciaisLojas />
      <CredenciaisCanais />
    </>
  );
}

function Lojas() {
  const lojas = useQuery({ queryKey: ["lojas"], queryFn: () => chamar(api.GET("/lojas")) });
  const status = useAcao(
    ({ codigo, ativa }: { codigo: string; ativa: boolean }) =>
      chamar(api.PATCH("/lojas/{codigo}/status", { params: { path: { codigo } }, body: { status_plataforma: ativa } })),
    { sucesso: "Loja atualizada.", recarregar: [["lojas"], ["status"]] },
  );

  return (
    <Cartao titulo="Lojas de origem">
      <Estado carregando={lojas.isLoading} erro={lojas.error} />
      {lojas.data?.map((loja) => (
        <div key={loja.id} className="linha-item">
          <Alternador rotulo={loja.nome} ligado={loja.status_plataforma} aoMudar={(ativa) => status.mutate({ codigo: loja.codigo, ativa })} />
          {loja.codigo === "mercado_livre" && (
            <a className="botao" href={`${URL_API}/oauth/mercado-livre/autorizar`} target="_blank" rel="noreferrer">
              Autorizar Mercado Livre
            </a>
          )}
        </div>
      ))}
      <p className="detalhe">
        A autorização do Mercado Livre é refeita quando a coleta retorna 401 ou quando você troca as credenciais.
      </p>
    </Cartao>
  );
}

function Canais() {
  const canais = useQuery({ queryKey: ["canais"], queryFn: () => chamar(api.GET("/canais-divulgacao")) });
  const status = useAcao(
    ({ codigo, ativo }: { codigo: string; ativo: boolean }) =>
      chamar(api.PATCH("/canais-divulgacao/{codigo}/status", { params: { path: { codigo } }, body: { status_plataforma: ativo } })),
    { sucesso: "Canal atualizado.", recarregar: [["canais"], ["status"]] },
  );

  return (
    <Cartao titulo="Canais de divulgação">
      <Estado carregando={canais.isLoading} erro={canais.error} />
      {canais.data?.map((canal) => (
        <div key={canal.id} className="linha-item">
          <Alternador rotulo={canal.nome} ligado={canal.status_plataforma} aoMudar={(ativo) => status.mutate({ codigo: canal.codigo, ativo })} />
        </div>
      ))}
      <p className="detalhe">Desligar um canal impede toda publicação nele, inclusive a manual.</p>
    </Cartao>
  );
}

function CredenciaisLojas() {
  const lojas = useQuery({ queryKey: ["lojas"], queryFn: () => chamar(api.GET("/lojas")) });
  const credenciais = useQuery({ queryKey: ["credenciais-lojas"], queryFn: () => chamar(api.GET("/credenciais-plataforma")) });
  const [lojaId, setLojaId] = useState("");
  const [tipo, setTipo] = useState("");
  const [valor, setValor] = useState("");

  const nomeLoja = Object.fromEntries((lojas.data ?? []).map((l) => [l.id, l.nome]));
  const recarregar = [["credenciais-lojas"]];

  const status = useAcao(
    ({ id, ativa }: { id: number; ativa: boolean }) =>
      chamar(
        api.PATCH("/credenciais-plataforma/{credencial_id}/status", {
          params: { path: { credencial_id: id } },
          body: { status_credencial: ativa ? "ativa" : "inativa" },
        }),
      ),
    { sucesso: "Credencial atualizada.", recarregar },
  );

  const criar = useAcao(
    () => chamar(api.POST("/credenciais-plataforma", { body: { plataforma_id: Number(lojaId), tipo_credencial: tipo, valor } })),
    { sucesso: "Credencial salva (criptografada).", recarregar },
  );

  return (
    <Cartao titulo="Credenciais das lojas">
      <p className="detalhe">
        Só pode haver uma credencial ativa de cada tipo por loja: para trocar, inative a atual e cadastre a nova. Os valores
        ficam criptografados e nunca são exibidos.
      </p>
      <Estado carregando={credenciais.isLoading} erro={credenciais.error} />
      {credenciais.data && (
        <div className="tabela-rolagem">
          <table>
            <thead>
              <tr>
                <th>Loja</th>
                <th>Tipo</th>
                <th>Status</th>
                <th>Atualizada</th>
              </tr>
            </thead>
            <tbody>
              {credenciais.data.map((c) => (
                <tr key={c.id}>
                  <td>{nomeLoja[c.plataforma_id]}</td>
                  <td>
                    <code>{c.tipo_credencial}</code>
                  </td>
                  <td>
                    <Alternador rotulo="" ligado={c.status_credencial === "ativa"} aoMudar={(ativa) => status.mutate({ id: c.id, ativa })} />
                    <Etiqueta status={c.status_credencial} />
                  </td>
                  <td>{formatarData(c.updated_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <form
        className="formulario-linha"
        onSubmit={(e) => {
          e.preventDefault();
          criar.mutate(undefined, { onSuccess: () => setValor("") });
        }}
      >
        <Campo rotulo="Loja">
          <select required value={lojaId} onChange={(e) => setLojaId(e.target.value)}>
            <option value="">Selecione</option>
            {lojas.data?.map((l) => (
              <option key={l.id} value={l.id}>
                {l.nome}
              </option>
            ))}
          </select>
        </Campo>
        <Campo rotulo="Tipo" dica="ML: client_id, client_secret, redirect_uri. Shopee: app_id, app_secret.">
          <input required value={tipo} onChange={(e) => setTipo(e.target.value)} list="tipos-loja" />
          <datalist id="tipos-loja">
            {["client_id", "client_secret", "redirect_uri", "app_id", "app_secret"].map((t) => (
              <option key={t} value={t} />
            ))}
          </datalist>
        </Campo>
        <Campo rotulo="Valor">
          <input required type="password" autoComplete="off" value={valor} onChange={(e) => setValor(e.target.value)} />
        </Campo>
        <button className="botao botao-principal" disabled={criar.isPending}>
          Salvar credencial
        </button>
      </form>
    </Cartao>
  );
}

function CredenciaisCanais() {
  const canais = useQuery({ queryKey: ["canais"], queryFn: () => chamar(api.GET("/canais-divulgacao")) });
  const credenciais = useQuery({ queryKey: ["credenciais-divulgacao"], queryFn: () => chamar(api.GET("/credenciais-divulgacao")) });
  const [canalId, setCanalId] = useState("");
  const [nome, setNome] = useState("");
  const [valor, setValor] = useState("");

  const nomeCanal = Object.fromEntries((canais.data ?? []).map((c) => [c.id, c.nome]));
  const recarregar = [["credenciais-divulgacao"]];

  const status = useAcao(
    ({ id, ativa }: { id: number; ativa: boolean }) =>
      chamar(
        api.PATCH("/credenciais-divulgacao/{credencial_id}/status", {
          params: { path: { credencial_id: id } },
          body: { status_credencial: ativa ? "ativa" : "inativa" },
        }),
      ),
    { sucesso: "Credencial atualizada.", recarregar },
  );

  const criar = useAcao(
    () =>
      chamar(
        api.POST("/credenciais-divulgacao", {
          body: { plataforma_divulgacao_id: Number(canalId), nome_credencial: nome, tipo_credencial: "bot_telegram", valor },
        }),
      ),
    { sucesso: "Token salvo (criptografado).", recarregar },
  );

  const telegram = canais.data?.filter((c) => c.codigo === "telegram") ?? [];

  return (
    <Cartao titulo="Credenciais dos canais">
      <p className="detalhe">Telegram: token do bot (@BotFather). O WhatsApp não usa credencial: a sessão fica no Chrome do projeto.</p>
      <Estado carregando={credenciais.isLoading} erro={credenciais.error} />
      {credenciais.data && credenciais.data.length > 0 && (
        <div className="tabela-rolagem">
          <table>
            <thead>
              <tr>
                <th>Nome</th>
                <th>Canal</th>
                <th>Tipo</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {credenciais.data.map((c) => (
                <tr key={c.id}>
                  <td>{c.nome_credencial}</td>
                  <td>{nomeCanal[c.plataforma_divulgacao_id]}</td>
                  <td>
                    <code>{c.tipo_credencial}</code>
                  </td>
                  <td>
                    <Alternador rotulo="" ligado={c.status_credencial === "ativa"} aoMudar={(ativa) => status.mutate({ id: c.id, ativa })} />
                    <Etiqueta status={c.status_credencial} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <form
        className="formulario-linha"
        onSubmit={(e) => {
          e.preventDefault();
          criar.mutate(undefined, { onSuccess: () => setValor("") });
        }}
      >
        <Campo rotulo="Canal">
          <select required value={canalId} onChange={(e) => setCanalId(e.target.value)}>
            <option value="">Selecione</option>
            {telegram.map((c) => (
              <option key={c.id} value={c.id}>
                {c.nome}
              </option>
            ))}
          </select>
        </Campo>
        <Campo rotulo="Nome">
          <input required value={nome} onChange={(e) => setNome(e.target.value)} placeholder="Bot principal" />
        </Campo>
        <Campo rotulo="Token do bot">
          <input required type="password" autoComplete="off" value={valor} onChange={(e) => setValor(e.target.value)} />
        </Campo>
        <button className="botao botao-principal" disabled={criar.isPending}>
          Salvar token
        </button>
      </form>
    </Cartao>
  );
}
