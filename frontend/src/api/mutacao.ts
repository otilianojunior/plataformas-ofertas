import { useMutation, useQueryClient } from "@tanstack/react-query";

import { textoDoErro, useAvisos } from "../components/ui";

/** Mutação com aviso de sucesso/erro e recarga das consultas afetadas. */
export function useAcao<A, R>(
  executar: (argumento: A) => Promise<R>,
  opcoes: { sucesso?: string | ((resultado: R) => string); recarregar?: string[][] } = {},
) {
  const cliente = useQueryClient();
  const avisar = useAvisos();

  return useMutation({
    mutationFn: executar,
    onSuccess: (resultado) => {
      const texto = typeof opcoes.sucesso === "function" ? opcoes.sucesso(resultado) : opcoes.sucesso;
      if (texto) avisar("ok", texto);
      for (const chave of opcoes.recarregar ?? []) cliente.invalidateQueries({ queryKey: chave });
    },
    onError: (erro) => avisar("erro", textoDoErro(erro)),
  });
}
