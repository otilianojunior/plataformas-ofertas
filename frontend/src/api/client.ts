import createClient from "openapi-fetch";

import type { components, paths } from "./schema";

export type Esquemas = components["schemas"];

// Em desenvolvimento o Vite repassa /api para a API; no build o painel é
// servido pela própria API, na mesma origem.
export const api = createClient<paths>({
  baseUrl: import.meta.env.DEV ? "/api" : "",
});

export class ErroApi extends Error {
  constructor(
    public status: number,
    mensagem: string,
    public detalhe?: unknown,
  ) {
    super(mensagem);
  }
}

function mensagemDoErro(erro: unknown): string {
  const detalhe = (erro as { detail?: unknown } | undefined)?.detail;

  if (typeof detalhe === "string") return detalhe;

  // 422 do Pydantic: lista de campos inválidos
  if (Array.isArray(detalhe)) {
    return detalhe
      .map((item: { loc?: unknown[]; msg?: string }) => {
        const campo = (item.loc ?? []).filter((p) => p !== "body").join(".");
        return campo ? `${campo}: ${item.msg}` : item.msg;
      })
      .join("; ");
  }

  // ex.: publicação manual sem nenhum grupo publicado
  if (detalhe && typeof detalhe === "object" && "mensagem" in detalhe) {
    return String((detalhe as { mensagem: unknown }).mensagem);
  }

  return "Erro inesperado na API.";
}

/** Executa uma chamada e devolve os dados, ou lança ErroApi com a mensagem da API. */
export async function chamar<T>(
  requisicao: Promise<{ data?: T; error?: unknown; response: Response }>,
): Promise<T> {
  let resultado;

  try {
    resultado = await requisicao;
  } catch {
    throw new ErroApi(0, "A API não respondeu. Ela está ligada? (make servico-status)");
  }

  const { data, error, response } = resultado;

  if (!response.ok || error !== undefined) {
    throw new ErroApi(response.status, mensagemDoErro(error), (error as { detail?: unknown })?.detail);
  }

  return data as T;
}
