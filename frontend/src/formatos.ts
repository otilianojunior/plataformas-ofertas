const moeda = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });
const dataHora = new Intl.DateTimeFormat("pt-BR", {
  day: "2-digit",
  month: "2-digit",
  hour: "2-digit",
  minute: "2-digit",
  timeZone: "America/Sao_Paulo",
});

export const formatarPreco = (valor: string | number | null | undefined) =>
  valor === null || valor === undefined || valor === "" ? "—" : moeda.format(Number(valor));

export const formatarPercentual = (valor: string | number | null | undefined) =>
  valor === null || valor === undefined ? "—" : `${Number(valor).toLocaleString("pt-BR", { maximumFractionDigits: 1 })}%`;

export const formatarData = (valor: string | null | undefined) =>
  valor ? dataHora.format(new Date(valor)) : "—";

export const formatarHora = (valor: string) => valor.slice(0, 5);

/** Rótulos legíveis para os status que a API devolve. */
const ROTULOS: Record<string, string> = {
  online: "Online",
  offline: "Offline",
  pausada: "Pausada",
  executando: "Executando",
  falhou: "Falhou",
  concluida: "Concluída",
  concluido: "Concluído",
  parcial: "Parcial",
  em_andamento: "Em andamento",
  interrompido: "Interrompido",
  pausado: "Pausado",
  publicando: "Publicando",
  publicada: "Publicada",
  pendente: "Pendente",
  ignorada: "Ignorada",
  gerado: "Gerado",
  erro: "Erro",
  ativo: "Ativo",
  encerrado: "Encerrado",
  ativa: "Ativa",
  inativa: "Inativa",
  monitor_offline: "Monitor offline",
  fora_da_janela: "Fora da janela",
  aguardando_intervalo: "Aguardando intervalo",
  pronta_para_execucao: "Pronta",
  plataforma_inativa: "Loja inativa",
  plataforma_nao_cadastrada: "Loja não cadastrada",
  destino_inativo: "Grupo inativo",
  canal_nao_suportado: "Canal não suportado",
};

export const rotulo = (status: string | null | undefined) =>
  status ? (ROTULOS[status] ?? status.replaceAll("_", " ")) : "—";

/** Tom de cor de cada status: ok, alerta, erro ou neutro. */
export function tomDoStatus(status: string | null | undefined): "ok" | "alerta" | "erro" | "neutro" {
  if (!status) return "neutro";
  if (["online", "concluida", "concluido", "publicada", "gerado", "ativo", "ativa", "publicando", "executando", "pronta_para_execucao", "em_andamento"].includes(status)) return "ok";
  if (["falhou", "erro", "offline", "monitor_offline", "plataforma_nao_cadastrada"].includes(status)) return "erro";
  if (["parcial", "pausada", "pausado", "interrompido", "fora_da_janela", "pendente", "ignorada", "destino_inativo", "plataforma_inativa", "inativa", "encerrado"].includes(status)) return "alerta";
  return "neutro";
}
