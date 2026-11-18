// Token do login guardado no navegador. Se o armazenamento estiver bloqueado,
// a sessão dura só enquanto a aba estiver aberta.
const CHAVE = "ofertas.sessao";

let emMemoria: string | null = null;

export function obterToken(): string | null {
  try {
    return localStorage.getItem(CHAVE) ?? emMemoria;
  } catch {
    return emMemoria;
  }
}

export function salvarToken(token: string): void {
  emMemoria = token;
  try {
    localStorage.setItem(CHAVE, token);
  } catch {
    /* fica só na memória */
  }
}

export function encerrarSessao(): void {
  emMemoria = null;
  try {
    localStorage.removeItem(CHAVE);
  } catch {
    /* nada a remover */
  }
}
