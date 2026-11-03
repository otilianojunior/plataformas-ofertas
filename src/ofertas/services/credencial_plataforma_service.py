from sqlalchemy.orm import Session

from ofertas.models.credencial_plataforma import CredencialPlataforma
from ofertas.repositories.credencial_plataforma_repository import (
    CredencialPlataformaRepository,
)
from ofertas.repositories.plataforma_repository import PlataformaRepository
from ofertas.core.security import (
    criptografar_credencial,
    descriptografar_credencial,
)


class CredencialPlataformaService:
    def __init__(
        self,
        credencial_repository: CredencialPlataformaRepository | None = None,
        plataforma_repository: PlataformaRepository | None = None,
    ) -> None:
        self.credencial_repository = (
            credencial_repository or CredencialPlataformaRepository()
        )
        self.plataforma_repository = (
            plataforma_repository or PlataformaRepository()
        )

    def listar(
        self,
        session: Session,
        plataforma_id: int | None = None,
    ) -> list[CredencialPlataforma]:
        if plataforma_id is not None:
            plataforma = self.plataforma_repository.buscar_por_id(
                session, plataforma_id
            )
            if plataforma is None:
                raise LookupError("Plataforma não encontrada.")

        return self.credencial_repository.listar(session, plataforma_id)

    def buscar_por_id(
        self,
        session: Session,
        credencial_id: int,
    ) -> CredencialPlataforma:
        credencial = self.credencial_repository.buscar_por_id(
            session, credencial_id
        )
        if credencial is None:
            raise LookupError("Credencial não encontrada.")

        return credencial

    def buscar_valor_ativo(
        self,
        session: Session,
        *,
        plataforma_codigo: str,
        tipo_credencial: str,
    ) -> str:
        plataforma = self.plataforma_repository.buscar_por_codigo(
            session,
            plataforma_codigo,
        )

        if plataforma is None:
            raise LookupError("Plataforma não encontrada.")

        credenciais = self.credencial_repository.buscar_ativas_por_tipo(
            session,
            plataforma.id,
            tipo_credencial,
        )

        if not credenciais:
            raise LookupError(
                f"Credencial ativa '{tipo_credencial}' não encontrada."
            )

        if len(credenciais) > 1:
            raise ValueError(
                f"Existe mais de uma credencial ativa do tipo "
                f"'{tipo_credencial}' para esta plataforma."
            )

        return descriptografar_credencial(
            credenciais[0].valor_criptografado
        )

    def criar(
        self,
        session: Session,
        *,
        plataforma_id: int,
        tipo_credencial: str,
        valor: str,
    ) -> CredencialPlataforma:
        tipo_credencial = tipo_credencial.strip()
        valor = valor.strip()

        if not tipo_credencial:
            raise ValueError("O tipo da credencial é obrigatório.")
        if not valor:
            raise ValueError("O valor da credencial é obrigatório.")

        plataforma = self.plataforma_repository.buscar_por_id(
            session, plataforma_id
        )
        
        if plataforma is None:
            raise LookupError("Plataforma não encontrada.")

        if not plataforma.status_plataforma:
            raise ValueError(
                "Não é possível cadastrar credenciais em uma plataforma inativa."
            )

        valor_criptografado = criptografar_credencial(valor)

        return self.credencial_repository.criar(
            session,
            plataforma_id=plataforma_id,
            tipo_credencial=tipo_credencial,
            valor_criptografado=valor_criptografado,
        )

    def atualizar_status(
        self,
        session: Session,
        credencial_id: int,
        status_credencial: str,
    ) -> CredencialPlataforma:
        if status_credencial not in {"ativa", "inativa"}:
            raise ValueError("Status inválido.")

        credencial = self.buscar_por_id(session, credencial_id)

        return self.credencial_repository.atualizar_status(
            session,
            credencial,
            status_credencial,
        )
