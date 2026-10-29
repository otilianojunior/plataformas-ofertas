from sqlalchemy.orm import Session

from ofertas.core.security import criptografar_credencial
from ofertas.models.credencial_divulgacao import CredencialDivulgacao
from ofertas.repositories.credencial_divulgacao_repository import (
    CredencialDivulgacaoRepository,
)
from ofertas.repositories.plataforma_divulgacao_repository import (
    PlataformaDivulgacaoRepository,
)


class CredencialDivulgacaoService:
    def __init__(
        self,
        credencial_repository=None,
        plataforma_repository=None,
    ):
        self.credencial_repository = (
            credencial_repository or CredencialDivulgacaoRepository()
        )
        self.plataforma_repository = (
            plataforma_repository or PlataformaDivulgacaoRepository()
        )

    def listar(
        self,
        session: Session,
        plataforma_divulgacao_id: int | None = None,
    ) -> list[CredencialDivulgacao]:
        if plataforma_divulgacao_id is not None:
            plataforma = self.plataforma_repository.buscar_por_id(
                session,
                plataforma_divulgacao_id,
            )
            if plataforma is None:
                raise LookupError("Canal de divulgação não encontrado.")

        return self.credencial_repository.listar(
            session,
            plataforma_divulgacao_id,
        )

    def buscar_por_id(
        self,
        session: Session,
        credencial_id: int,
    ) -> CredencialDivulgacao:
        credencial = self.credencial_repository.buscar_por_id(
            session,
            credencial_id,
        )
        if credencial is None:
            raise LookupError("Credencial de divulgação não encontrada.")

        return credencial

    def criar(
        self,
        session: Session,
        *,
        plataforma_divulgacao_id: int,
        tipo_credencial: str,
        valor: str,
    ) -> CredencialDivulgacao:
        tipo_credencial = tipo_credencial.strip()
        valor = valor.strip()

        if not tipo_credencial:
            raise ValueError("O tipo da credencial é obrigatório.")
        if not valor:
            raise ValueError("O valor da credencial é obrigatório.")

        plataforma = self.plataforma_repository.buscar_por_id(
            session,
            plataforma_divulgacao_id,
        )
        
        if plataforma is None:
            raise LookupError("Canal de divulgação não encontrado.")

        if not plataforma.status_plataforma:
            raise ValueError(
                "Não é possível cadastrar credenciais em um canal de divulgação inativo."
            )

        valor_criptografado = criptografar_credencial(valor)

        return self.credencial_repository.criar(
            session,
            plataforma_divulgacao_id=plataforma_divulgacao_id,
            tipo_credencial=tipo_credencial,
            valor_criptografado=valor_criptografado,
        )

    def atualizar_status(
        self,
        session: Session,
        credencial_id: int,
        status_credencial: str,
    ) -> CredencialDivulgacao:
        if status_credencial not in {"ativa", "inativa"}:
            raise ValueError("Status da credencial inválido.")

        credencial = self.buscar_por_id(session, credencial_id)

        return self.credencial_repository.atualizar_status(
            session,
            credencial,
            status_credencial,
        )
