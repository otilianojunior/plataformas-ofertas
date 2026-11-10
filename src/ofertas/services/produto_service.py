
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from ofertas.models.historico_preco import HistoricoPreco
from ofertas.models.plataforma import Plataforma
from ofertas.models.plataforma_categoria import PlataformaCategoria
from ofertas.models.produto import Produto
from ofertas.repositories.produto_repository import ProdutoRepository
from ofertas.schemas.produto import ProdutoCreate, ProdutoUpdate


class ProdutoService:
    """Implementa as regras de negócio dos produtos."""

    def __init__(
        self,
        repository: ProdutoRepository | None = None,
    ) -> None:
        self.repository = repository or ProdutoRepository()

    def listar(self, session: Session) -> list[Produto]:
        return self.repository.listar(session)

    def buscar_por_id(
        self,
        session: Session,
        produto_id: int,
    ) -> Produto | None:
        return self.repository.buscar_por_id(session, produto_id)

    def _validar_categoria(
        self,
        session: Session,
        plataforma_id: int,
        categoria_id: int | None,
    ) -> PlataformaCategoria | None:
        if categoria_id is None:
            return None

        categoria = session.get(PlataformaCategoria, categoria_id)

        if categoria is None:
            raise LookupError(
                f"Categoria de ID '{categoria_id}' não encontrada."
            )

        if categoria.plataforma_id != plataforma_id:
            raise ValueError(
                "A categoria informada não pertence à plataforma do produto."
            )

        return categoria

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

    def _registrar_historico(
        self,
        session: Session,
        produto: Produto,
        origem: str,
    ) -> None:
        if produto.preco_atual is None:
            return

        session.add(
            HistoricoPreco(
                produto_id=produto.id,
                preco=produto.preco_atual,
                origem=origem,
            )
        )

    def criar(
        self,
        session: Session,
        dados: ProdutoCreate,
    ) -> Produto:
        plataforma = session.get(Plataforma, dados.plataforma_id)

        if plataforma is None:
            raise LookupError(
                f"Plataforma de ID '{dados.plataforma_id}' não encontrada."
            )

        if not plataforma.status_plataforma:
            raise ValueError(
                "Não é possível cadastrar produtos em uma plataforma inativa."
            )

        categoria = self._validar_categoria(
            session,
            dados.plataforma_id,
            dados.categoria_id,
        )

        valores = dados.model_dump()

        id_item = valores["id_item_plataforma"].strip()
        titulo = valores["titulo"].strip()

        if not id_item or not titulo:
            raise ValueError(
                "O identificador externo e o título não podem ficar vazios."
            )

        existente = self.repository.buscar_por_item(
            session,
            dados.plataforma_id,
            id_item,
        )

        if existente is not None:
            raise ValueError(
                f"O item '{id_item}' já está cadastrado nesta plataforma."
            )

        for campo in ("url", "imagem_url", "url_afiliada"):
            if valores.get(campo) is not None:
                valores[campo] = str(valores[campo])

        valores["id_item_plataforma"] = id_item
        valores["titulo"] = titulo
        valores["status_link_afiliado"] = (
            "gerado" if valores.get("url_afiliada") else "pendente"
        )

        produto = self.repository.criar(session, valores)

        self._atualizar_elegibilidade(produto, categoria)
        self._registrar_historico(session, produto, "cadastro_manual")

        session.flush()
        return produto

    def atualizar(
        self,
        session: Session,
        produto_id: int,
        dados: ProdutoUpdate,
    ) -> Produto | None:
        produto = self.repository.buscar_por_id(session, produto_id)

        if produto is None:
            return None

        alteracoes = dados.model_dump(exclude_unset=True)

        categoria_id = alteracoes.get(
            "categoria_id",
            produto.categoria_id,
        )

        categoria = self._validar_categoria(
            session,
            produto.plataforma_id,
            categoria_id,
        )

        if "titulo" in alteracoes:
            titulo = alteracoes["titulo"].strip()

            if not titulo:
                raise ValueError("O título não pode ficar vazio.")

            alteracoes["titulo"] = titulo

        preco_anterior = produto.preco_atual

        for campo in ("url", "imagem_url", "url_afiliada"):
            if campo in alteracoes and alteracoes[campo] is not None:
                alteracoes[campo] = str(alteracoes[campo])

        if "url_afiliada" in alteracoes:
            alteracoes["status_link_afiliado"] = (
                "gerado" if alteracoes["url_afiliada"] else "pendente"
            )

        for campo, valor in alteracoes.items():
            setattr(produto, campo, valor)

        self._atualizar_elegibilidade(produto, categoria)

        if preco_anterior != produto.preco_atual:
            self._registrar_historico(
                session,
                produto,
                "atualizacao_manual",
            )

        session.flush()
        return produto

    def registrar_coleta(
        self,
        session: Session,
        dados: dict,
    ) -> Produto:
        """Cria ou atualiza um produto encontrado durante a coleta."""

        dados = dados.copy()
        agora = datetime.now(timezone.utc)

        dados["ultima_coleta_em"] = agora

        id_item = str(dados["id_item_plataforma"]).strip()

        if not id_item:
            raise ValueError("O identificador externo não pode ficar vazio.")

        dados["id_item_plataforma"] = id_item

        existente = self.repository.buscar_por_item(
            session,
            dados["plataforma_id"],
            id_item,
        )

        categoria_id = dados.get(
            "categoria_id",
            existente.categoria_id if existente else None,
        )

        categoria = self._validar_categoria(
            session,
            dados["plataforma_id"],
            categoria_id,
        )

        if existente is None:
            dados.setdefault("status_monitoramento", "ativo")
            dados.setdefault("disponivel", True)
            dados.setdefault("status_link_afiliado", "pendente")
            dados.setdefault("primeira_coleta_em", agora)

            produto = self.repository.criar(session, dados)

            self._registrar_historico(
                session,
                produto,
                "coleta_api",
            )

        else:
            preco_anterior = existente.preco_atual

            produto = self.repository.atualizar_coleta(
                session,
                existente,
                dados,
            )

            if preco_anterior != produto.preco_atual:
                self._registrar_historico(
                    session,
                    produto,
                    "coleta_api",
                )

        self._atualizar_elegibilidade(produto, categoria)

        session.flush()
        return produto

    def atualizar_status_monitoramento(
        self,
        session: Session,
        produto_id: int,
        status: str,
    ) -> Produto | None:
        if status not in {"ativo", "pausado", "encerrado"}:
            raise ValueError("Status de monitoramento inválido.")

        produto = self.repository.buscar_por_id(session, produto_id)

        if produto is None:
            return None

        produto.status_monitoramento = status

        categoria = self._validar_categoria(
            session,
            produto.plataforma_id,
            produto.categoria_id,
        )

        self._atualizar_elegibilidade(produto, categoria)

        session.flush()
        return produto

    def atualizar_posicoes_selecao_categoria(
        self,
        session: Session,
        categoria_id: int,
        posicoes: dict[int, int],
    ) -> None:
        """Atualiza as posições dos produtos selecionados na categoria."""

        self.repository.atualizar_posicoes_selecao_categoria(
            session,
            categoria_id,
            posicoes,
        )
