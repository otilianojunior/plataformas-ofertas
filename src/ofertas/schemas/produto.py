
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator


class ProdutoCreate(BaseModel):
    plataforma_id: int = Field(gt=0)
    categoria_id: int | None = Field(default=None, gt=0)

    id_produto_plataforma: str | None = Field(
        default=None,
        max_length=150,
    )
    id_item_plataforma: str = Field(min_length=1, max_length=150)

    titulo: str = Field(min_length=1, max_length=500)
    descricao: str | None = None

    url: HttpUrl
    imagem_url: HttpUrl | None = None
    url_afiliada: HttpUrl | None = None

    preco_atual: Decimal = Field(
        gt=0,
        max_digits=12,
        decimal_places=2,
    )
    preco_original: Decimal | None = Field(
        default=None,
        ge=0,
        max_digits=12,
        decimal_places=2,
    )
    percentual_desconto: Decimal | None = Field(
        default=None,
        ge=0,
        le=100,
        max_digits=5,
        decimal_places=2,
    )


class ProdutoUpdate(BaseModel):
    categoria_id: int | None = Field(default=None, gt=0)

    titulo: str | None = Field(
        default=None,
        min_length=1,
        max_length=500,
    )
    descricao: str | None = None

    url: HttpUrl | None = None
    imagem_url: HttpUrl | None = None
    url_afiliada: HttpUrl | None = None

    preco_atual: Decimal | None = Field(
        default=None,
        gt=0,
        max_digits=12,
        decimal_places=2,
    )
    preco_original: Decimal | None = Field(
        default=None,
        ge=0,
        max_digits=12,
        decimal_places=2,
    )
    percentual_desconto: Decimal | None = Field(
        default=None,
        ge=0,
        le=100,
        max_digits=5,
        decimal_places=2,
    )

    disponivel: bool | None = None
    status_monitoramento: str | None = None

    @model_validator(mode="after")
    def validar_campos_informados(self):
        if not self.model_fields_set:
            raise ValueError("Informe pelo menos um campo para atualizar.")

        if (
            self.status_monitoramento is not None
            and self.status_monitoramento
            not in {"ativo", "pausado", "encerrado"}
        ):
            raise ValueError("Status de monitoramento inválido.")

        return self


class ProdutoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    plataforma_id: int
    categoria_id: int | None

    id_produto_plataforma: str | None
    id_item_plataforma: str

    titulo: str
    descricao: str | None

    url: str
    imagem_url: str | None
    url_afiliada: str | None

    preco_atual: Decimal
    preco_original: Decimal | None
    percentual_desconto: Decimal | None

    disponivel: bool
    status_monitoramento: str
    elegivel_divulgacao: bool

    status_link_afiliado: str
    metodo_geracao_link_afiliado: str | None
    identificador_rastreamento: str | None
    erro_geracao_link_afiliado: str | None
    link_afiliado_gerado_em: datetime | None

    primeira_coleta_em: datetime
    ultima_coleta_em: datetime
    proxima_coleta_em: datetime | None

    created_at: datetime
    updated_at: datetime
