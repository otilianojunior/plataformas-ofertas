from decimal import Decimal
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session

from ofertas.models.destino_divulgacao import DestinoDivulgacao
from ofertas.models.plataforma import Plataforma
from ofertas.models.plataforma_categoria import PlataformaCategoria
from ofertas.models.plataforma_divulgacao import PlataformaDivulgacao
from ofertas.repositories.categoria_repository import CategoriaRepository
from ofertas.schemas.categoria import CategoriaCreate


class CategoriaService:
    """Implementa as regras de negócio das categorias."""

    def __init__(
        self,
        repository: CategoriaRepository | None = None,
    ) -> None:
        self.repository = repository or CategoriaRepository()

    def listar(
        self,
        session: Session,
        plataforma_id: int | None = None,
    ) -> list[PlataformaCategoria]:
        return self.repository.listar(session, plataforma_id)

    def buscar_por_id(
        self,
        session: Session,
        categoria_id: int,
    ) -> PlataformaCategoria | None:
        return self.repository.buscar_por_id(session, categoria_id)

    def _validar_destino_telegram(
        self,
        session: Session,
        destino_id: int | None,
    ) -> None:
        """Valida se o destino informado pertence ao Telegram."""
        if destino_id is None:
            return

        destino = session.get(DestinoDivulgacao, destino_id)

        if destino is None:
            raise LookupError(
                f"Destino de divulgação de ID '{destino_id}' não encontrado."
            )

        plataforma = session.get(
            PlataformaDivulgacao,
            destino.plataforma_divulgacao_id,
        )

        if plataforma is None:
            raise LookupError(
                "Canal de divulgação do destino não encontrado."
            )

        if plataforma.codigo.lower() != "telegram":
            raise ValueError(
                "A categoria só pode ser associada a um destino do Telegram."
            )

    def criar(
        self,
        session: Session,
        dados: CategoriaCreate,
    ) -> PlataformaCategoria:
        plataforma = session.get(Plataforma, dados.plataforma_id)

        if plataforma is None:
            raise LookupError(
                f"Plataforma de ID '{dados.plataforma_id}' não encontrada."
            )

        self._validar_destino_telegram(
            session,
            dados.destino_divulgacao_id,
        )

        id_externo = dados.id_categoria_plataforma.strip()
        nome = dados.nome_categoria.strip()
        etiqueta = (
            dados.etiqueta_afiliado.strip()
            if dados.etiqueta_afiliado
            else None
        )

        if not id_externo or not nome:
            raise ValueError(
                "O identificador externo e o nome da categoria "
                "não podem ficar vazios."
            )

        existente = self.repository.buscar_por_id_externo(
            session,
            dados.plataforma_id,
            id_externo,
        )

        if existente is not None:
            raise ValueError(
                f"A categoria '{id_externo}' já está cadastrada nesta plataforma."
            )

        return self.repository.criar(
            session,
            plataforma_id=dados.plataforma_id,
            id_categoria_plataforma=id_externo,
            nome_categoria=nome,
            desconto_minimo_percentual=dados.desconto_minimo_percentual,
            etiqueta_afiliado=etiqueta,
            destino_divulgacao_id=dados.destino_divulgacao_id,
            status_categoria=dados.status_categoria,
        )

    def atualizar_status(
        self,
        session: Session,
        categoria_id: int,
        ativo: bool,
    ) -> PlataformaCategoria:
        categoria = self.repository.buscar_por_id(session, categoria_id)

        if categoria is None:
            raise LookupError(
                f"Categoria de ID '{categoria_id}' não encontrada."
            )

        return self.repository.atualizar_status(session, categoria, ativo)

    def atualizar_desconto_minimo(
        self,
        session: Session,
        categoria_id: int,
        desconto_minimo_percentual: Decimal,
    ) -> PlataformaCategoria:
        categoria = self.repository.buscar_por_id(session, categoria_id)

        if categoria is None:
            raise LookupError(
                f"Categoria de ID '{categoria_id}' não encontrada."
            )

        return self.repository.atualizar_desconto_minimo(
            session,
            categoria,
            desconto_minimo_percentual,
        )

    def atualizar_etiqueta_afiliado(
        self,
        session: Session,
        categoria_id: int,
        etiqueta: str | None,
    ) -> PlataformaCategoria:
        categoria = self.repository.buscar_por_id(session, categoria_id)

        if categoria is None:
            raise LookupError(
                f"Categoria de ID '{categoria_id}' não encontrada."
            )

        etiqueta_normalizada = etiqueta.strip() if etiqueta else None

        return self.repository.atualizar_etiqueta_afiliado(
            session,
            categoria,
            etiqueta_normalizada,
        )

    def atualizar_destino_divulgacao(
        self,
        session: Session,
        categoria_id: int,
        destino_id: int | None,
    ) -> PlataformaCategoria:
        categoria = self.repository.buscar_por_id(session, categoria_id)

        if categoria is None:
            raise LookupError(
                f"Categoria de ID '{categoria_id}' não encontrada."
            )

        self._validar_destino_telegram(session, destino_id)

        return self.repository.atualizar_destino_divulgacao(
            session,
            categoria,
            destino_id,
        )


    TAMANHO_LOTE_SELECAO = 10
    PERIODO_RENOVACAO_DIAS = 7
    LIMITE_MAXIMO_SELECAO = 1000

    def preparar_selecao_coleta(
        self,
        session: Session,
        categoria: PlataformaCategoria,
    ) -> PlataformaCategoria:
        """Reinicia a seleção quando completar sete dias."""

        agora = datetime.now(timezone.utc)
        renovacao = categoria.selecao_renovada_em

        if renovacao is not None and renovacao.tzinfo is None:
            renovacao = renovacao.replace(tzinfo=timezone.utc)

        precisa_renovar = (
            renovacao is None
            or agora - renovacao
            >= timedelta(days=self.PERIODO_RENOVACAO_DIAS)
        )

        if not precisa_renovar:
            return categoria

        return self.repository.atualizar_selecao(
            session,
            categoria,
            limite_produtos_selecao=self.TAMANHO_LOTE_SELECAO,
            selecao_renovada_em=agora,
        )

    def avancar_selecao_coleta(
        self,
        session: Session,
        categoria: PlataformaCategoria,
        total_resultados: int,
    ) -> PlataformaCategoria:
        """Amplia a seleção em até dez produtos quando há mais resultados."""

        limite_atual = categoria.limite_produtos_selecao

        if total_resultados <= limite_atual:
            return categoria

        proximo_limite = min(
            limite_atual + self.TAMANHO_LOTE_SELECAO,
            total_resultados,
            self.LIMITE_MAXIMO_SELECAO,
        )

        if proximo_limite <= limite_atual:
            return categoria

        return self.repository.atualizar_selecao(
            session,
            categoria,
            limite_produtos_selecao=proximo_limite,
            selecao_renovada_em=categoria.selecao_renovada_em,
        )
