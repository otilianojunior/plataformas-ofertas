
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from ofertas.models.oferta import Oferta
from ofertas.models.plataforma import Plataforma
from ofertas.models.plataforma_categoria import PlataformaCategoria
from ofertas.repositories.oferta_repository import OfertaRepository
from ofertas.schemas.oferta import OfertaCreate, OfertaUpdate


class OfertaService:
    """Implementa as regras de negócio das ofertas."""

    def __init__(self, repository: OfertaRepository | None = None) -> None:
        self.repository = repository or OfertaRepository()

    def listar(self, session: Session) -> list[Oferta]:
        return self.repository.listar(session)

    def buscar_por_id(self, session: Session, oferta_id: int) -> Oferta | None:
        return self.repository.buscar_por_id(session, oferta_id)

    def criar(self, session: Session, dados: OfertaCreate) -> Oferta:
        plataforma = session.get(Plataforma, dados.plataforma_id)

        if plataforma is None:
            raise LookupError(
                f"Plataforma de ID '{dados.plataforma_id}' não encontrada."
            )

        if not plataforma.status_plataforma:
            raise ValueError(
                "Não é possível cadastrar ofertas em uma plataforma inativa."
            )

        if dados.categoria_id is not None:
            categoria = session.get(
                PlataformaCategoria,
                dados.categoria_id,
            )

            if categoria is None:
                raise LookupError(
                    f"Categoria de ID '{dados.categoria_id}' não encontrada."
                )

            if categoria.plataforma_id != dados.plataforma_id:
                raise ValueError(
                    "A categoria informada não pertence à plataforma da oferta."
                )

        id_item = dados.id_item_plataforma.strip()
        titulo = dados.titulo.strip()

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

        agora = datetime.now(timezone.utc)
        expira_em = dados.expira_em

        if expira_em.tzinfo is None:
            raise ValueError(
                "A data de expiração deve incluir o fuso horário."
            )

        if expira_em <= agora:
            raise ValueError(
                "A data de expiração deve estar no futuro."
            )

        valores = dados.model_dump()
        valores["id_item_plataforma"] = id_item
        valores["titulo"] = titulo
        valores["url"] = str(dados.url)
        valores["affiliate_url"] = (
            str(dados.affiliate_url) if dados.affiliate_url else None
        )
        valores["imagem_url"] = (
            str(dados.imagem_url) if dados.imagem_url else None
        )

        return self.repository.criar(session, valores)

    def atualizar(
        self,
        session: Session,
        oferta_id: int,
        dados: OfertaUpdate,
    ) -> Oferta | None:
        oferta = self.repository.buscar_por_id(session, oferta_id)

        if oferta is None:
            return None

        alteracoes = dados.model_dump(exclude_unset=True)

        if (
            "categoria_id" in alteracoes
            and alteracoes["categoria_id"] is not None
        ):
            categoria = session.get(
                PlataformaCategoria,
                alteracoes["categoria_id"],
            )

            if categoria is None:
                raise LookupError(
                    f"Categoria de ID '{alteracoes['categoria_id']}' não encontrada."
                )

            if categoria.plataforma_id != oferta.plataforma_id:
                raise ValueError(
                    "A categoria informada não pertence à plataforma da oferta."
                )

        if "titulo" in alteracoes:
            titulo = alteracoes["titulo"].strip()

            if not titulo:
                raise ValueError("O título não pode ficar vazio.")

            alteracoes["titulo"] = titulo

        if "expira_em" in alteracoes:
            expira_em = alteracoes["expira_em"]

            if expira_em is None or expira_em.tzinfo is None:
                raise ValueError(
                    "A data de expiração deve incluir o fuso horário."
                )

            if expira_em <= datetime.now(timezone.utc):
                raise ValueError(
                    "A data de expiração deve estar no futuro."
                )

        for campo, valor in alteracoes.items():
            if campo in {"url", "affiliate_url", "imagem_url"}:
                valor = str(valor) if valor is not None else None

            setattr(oferta, campo, valor)

        session.flush()
        return oferta

    def atualizar_status(
        self,
        session: Session,
        oferta_id: int,
        ativo: bool,
    ) -> Oferta | None:
        oferta = self.repository.buscar_por_id(session, oferta_id)

        if oferta is None:
            return None

        oferta.status_oferta = ativo
        session.flush()

        return oferta
