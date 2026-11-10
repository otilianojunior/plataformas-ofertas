import logging
from collections import defaultdict, deque
from collections.abc import Sequence
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlsplit

from sqlalchemy.orm import Session

from ofertas.affiliates.mercado_livre_client import (
    MercadoLivreAffiliateClient,
)
from ofertas.models.plataforma import Plataforma
from ofertas.models.plataforma_categoria import PlataformaCategoria
from ofertas.models.produto import Produto
from ofertas.repositories.produto_repository import ProdutoRepository


logger = logging.getLogger(__name__)


class MercadoLivreAffiliateService:
    """Coordena a geração e o registro de links afiliados."""

    # Usamos inicialmente o tamanho já validado no teste real.
    # O limite máximo da API será investigado separadamente.
    TAMANHO_LOTE_PADRAO = 20

    def __init__(
        self,
        repository: ProdutoRepository | None = None,
        client: MercadoLivreAffiliateClient | None = None,
        tamanho_lote: int = TAMANHO_LOTE_PADRAO,
    ) -> None:
        if tamanho_lote < 1:
            raise ValueError("O tamanho do lote deve ser maior que zero.")

        self.repository = repository or ProdutoRepository()
        self.client = client or MercadoLivreAffiliateClient()
        self.tamanho_lote = tamanho_lote

    def gerar_pendentes(
        self,
        session: Session,
        plataforma_id: int,
        produto_ids: Sequence[int] | None = None,
    ) -> dict[str, Any]:
        """Gera links afiliados para produtos pendentes do Mercado Livre."""

        plataforma = session.get(Plataforma, plataforma_id)

        if plataforma is None:
            raise LookupError(
                f"Plataforma de ID '{plataforma_id}' não encontrada."
            )

        if plataforma.codigo != "mercado_livre":
            raise ValueError(
                "Este serviço aceita somente a plataforma Mercado Livre."
            )

        produtos = self.repository.listar_pendentes_para_geracao_afiliado(
            session,
            plataforma_id,
            produto_ids,
        )

        resultado: dict[str, Any] = {
            "total_encontrados": len(produtos),
            "total_gerados": 0,
            "total_erros": 0,
            "total_lotes": 0,
            "erros": [],
        }

        grupos: dict[
            str,
            list[tuple[Produto, PlataformaCategoria]],
        ] = {}

        for produto, categoria in produtos:
            if categoria is None:
                self._registrar_erro(
                    produto,
                    None,
                    "Produto sem categoria associada.",
                )
                self._adicionar_erro(
                    resultado,
                    produto,
                    "Produto sem categoria associada.",
                )
                continue

            etiqueta = (
                categoria.etiqueta_afiliado.strip()
                if categoria.etiqueta_afiliado
                else ""
            )

            if not etiqueta:
                mensagem = (
                    f"A categoria '{categoria.nome_categoria}' "
                    "não possui etiqueta de afiliado."
                )
                self._registrar_erro(produto, categoria, mensagem)
                self._adicionar_erro(resultado, produto, mensagem)
                continue

            url = produto.url.strip() if produto.url else ""

            if not self._url_valida(url):
                mensagem = "Produto possui uma URL inválida."
                self._registrar_erro(produto, categoria, mensagem)
                self._adicionar_erro(resultado, produto, mensagem)
                continue

            grupos.setdefault(etiqueta, []).append(
                (produto, categoria)
            )

        session.flush()

        for etiqueta, itens in grupos.items():
            for inicio in range(0, len(itens), self.tamanho_lote):
                lote = itens[
                    inicio:inicio + self.tamanho_lote
                ]

                urls = [produto.url.strip() for produto, _ in lote]

                resultado["total_lotes"] += 1

                try:
                    resposta = self.client.create_links(
                        urls=urls,
                        tag=etiqueta,
                    )

                except Exception as erro:
                    logger.exception(
                        "Falha ao gerar links afiliados para um lote "
                        "com a etiqueta '%s'.",
                        etiqueta,
                    )

                    mensagem = (
                        f"{type(erro).__name__}: {erro}"
                    )

                    for produto, categoria in lote:
                        self._registrar_erro(
                            produto,
                            categoria,
                            mensagem,
                            etiqueta=etiqueta,
                            tentativa_api=True,
                        )
                        self._adicionar_erro(
                            resultado,
                            produto,
                            mensagem,
                        )

                    session.flush()
                    continue

                self._processar_resposta(
                    session=session,
                    lote=lote,
                    etiqueta=etiqueta,
                    resposta=resposta,
                    resultado=resultado,
                )

        session.flush()
        return resultado

    def _extrair_id_produto_catalogo(
        self,
        url: str,
    ) -> str | None:
        """Extrai o identificador do produto presente em /p/MLB..."""

        try:
            partes = [
                parte
                for parte in urlsplit(url).path.split("/")
                if parte
            ]
        except ValueError:
            return None

        for indice, parte in enumerate(partes[:-1]):
            identificador = partes[indice + 1].upper()

            if (
                parte == "p"
                and identificador.startswith("MLB")
                and identificador[3:].isdigit()
            ):
                return identificador

        return None

    def _processar_resposta(
        self,
        session: Session,
        lote: list[tuple[Produto, PlataformaCategoria]],
        etiqueta: str,
        resposta: Any,
        resultado: dict[str, Any],
    ) -> None:
        """Associa os resultados pela URL ou pelo ID do produto."""

        if not isinstance(resposta, dict):
            self._registrar_falha_lote(
                session,
                lote,
                etiqueta,
                "Resposta inválida do gerador de links.",
                resultado,
            )
            return

        status = resposta.get("status")

        if status is not None and status not in (200, "200"):
            self._registrar_falha_lote(
                session,
                lote,
                etiqueta,
                f"Mercado Livre retornou status inesperado: {status}.",
                resultado,
            )
            return

        itens_resposta = resposta.get("urls")

        if not isinstance(itens_resposta, list):
            self._registrar_falha_lote(
                session,
                lote,
                etiqueta,
                "Resposta do Mercado Livre não contém a lista esperada.",
                resultado,
            )
            return

        produtos_por_url = defaultdict(deque)
        produtos_por_catalogo = defaultdict(list)
        resultados_por_catalogo = defaultdict(int)

        for produto, categoria in lote:
            url = produto.url.strip()

            produtos_por_url[url].append((produto, categoria))

            identificador = self._extrair_id_produto_catalogo(url)

            if identificador:
                produtos_por_catalogo[identificador].append(
                    (produto, categoria)
                )

        for item in itens_resposta:
            if not isinstance(item, dict):
                continue

            url_original = item.get("origin_url")

            if isinstance(url_original, str):
                identificador = (
                    self._extrair_id_produto_catalogo(url_original)
                )

                if identificador:
                    resultados_por_catalogo[identificador] += 1

        produtos_atribuidos = set()

        for item in itens_resposta:
            if not isinstance(item, dict):
                continue

            url_original = item.get("origin_url")

            if not isinstance(url_original, str):
                continue

            correspondencia = None
            fila = produtos_por_url.get(url_original)

            if fila:
                while (
                    fila
                    and fila[0][0].id in produtos_atribuidos
                ):
                    fila.popleft()

                if fila:
                    correspondencia = fila.popleft()

            if correspondencia is None:
                identificador = (
                    self._extrair_id_produto_catalogo(url_original)
                )

                candidatos = [
                    par
                    for par in produtos_por_catalogo.get(
                        identificador,
                        [],
                    )
                    if par[0].id not in produtos_atribuidos
                ]

                if (
                    identificador
                    and len(candidatos) == 1
                    and resultados_por_catalogo[identificador] == 1
                ):
                    correspondencia = candidatos[0]

                    logger.info(
                        "Produto associado pelo ID de catálogo: %s",
                        identificador,
                    )

            if correspondencia is None:
                logger.warning(
                    "Não foi possível associar o resultado. "
                    "URL original retornada: %s",
                    url_original,
                )
                continue

            produto, categoria = correspondencia
            produtos_atribuidos.add(produto.id)

            link = item.get("short_url")

            if isinstance(link, str) and self._url_valida(link):
                self._registrar_sucesso(
                    produto,
                    categoria,
                    link,
                    etiqueta,
                )
                resultado["total_gerados"] += 1

            else:
                mensagem = self._mensagem_erro_item(item)

                self._registrar_erro(
                    produto,
                    categoria,
                    mensagem,
                    etiqueta=etiqueta,
                    tentativa_api=True,
                )

                self._adicionar_erro(
                    resultado,
                    produto,
                    mensagem,
                )

        for produto, categoria in lote:
            if produto.id in produtos_atribuidos:
                continue

            mensagem = (
                "O Mercado Livre não retornou um resultado "
                "correspondente à URL deste produto."
            )

            self._registrar_erro(
                produto,
                categoria,
                mensagem,
                etiqueta=etiqueta,
                tentativa_api=True,
            )

            self._adicionar_erro(
                resultado,
                produto,
                mensagem,
            )

        session.flush()

    def _registrar_sucesso(
        self,
        produto: Produto,
        categoria: PlataformaCategoria,
        link: str,
        etiqueta: str,
    ) -> None:
        if not produto.id_produto_plataforma:
            produto.id_produto_plataforma = (
                self._extrair_id_produto_catalogo(produto.url)
            )

        produto.url_afiliada = link
        produto.status_link_afiliado = "gerado"
        produto.metodo_geracao_link_afiliado = "api"
        produto.identificador_rastreamento = etiqueta
        produto.erro_geracao_link_afiliado = None
        produto.link_afiliado_gerado_em = datetime.now(timezone.utc)

        self._atualizar_elegibilidade(produto, categoria)

    def _registrar_erro(
        self,
        produto: Produto,
        categoria: PlataformaCategoria | None,
        mensagem: str,
        etiqueta: str | None = None,
        tentativa_api: bool = False,
    ) -> None:
        produto.status_link_afiliado = "erro"
        produto.metodo_geracao_link_afiliado = (
            "api" if tentativa_api else None
        )
        produto.identificador_rastreamento = (
            etiqueta if tentativa_api else None
        )
        produto.erro_geracao_link_afiliado = mensagem[:4000]
        produto.link_afiliado_gerado_em = None

        self._atualizar_elegibilidade(produto, categoria)

    def _registrar_falha_lote(
        self,
        session: Session,
        lote: list[tuple[Produto, PlataformaCategoria]],
        etiqueta: str,
        mensagem: str,
        resultado: dict[str, Any],
    ) -> None:
        for produto, categoria in lote:
            self._registrar_erro(
                produto,
                categoria,
                mensagem,
                etiqueta=etiqueta,
                tentativa_api=True,
            )
            self._adicionar_erro(resultado, produto, mensagem)

        session.flush()

    def _adicionar_erro(
        self,
        resultado: dict[str, Any],
        produto: Produto,
        mensagem: str,
    ) -> None:
        resultado["total_erros"] += 1
        resultado["erros"].append(
            {
                "produto_id": produto.id,
                "mensagem": mensagem,
            }
        )

    def _mensagem_erro_item(self, item: dict) -> str:
        for campo in ("error", "error_message", "message"):
            valor = item.get(campo)

            if valor:
                return str(valor)[:4000]

        return (
            "O Mercado Livre não retornou um link afiliado "
            "válido para este produto."
        )

    def _url_valida(self, url: str) -> bool:
        if not url:
            return False

        try:
            parsed = urlsplit(url)

        except ValueError:
            return False

        return (
            parsed.scheme in {"http", "https"}
            and bool(parsed.netloc)
        )

    def _atualizar_elegibilidade(
        self,
        produto: Produto,
        categoria: PlataformaCategoria | None,
    ) -> None:
        desconto_minimo = (
            categoria.desconto_minimo_percentual
            if categoria is not None
            else None
        )

        desconto_atingido = (
            desconto_minimo is not None
            and produto.percentual_desconto is not None
            and produto.percentual_desconto >= desconto_minimo
        )

        produto.elegivel_divulgacao = bool(
            produto.status_monitoramento == "ativo"
            and produto.disponivel
            and desconto_atingido
            and produto.status_link_afiliado == "gerado"
            and produto.url_afiliada
        )