import unittest
from unittest.mock import Mock

from ofertas.models.plataforma import Plataforma
from ofertas.schemas.plataforma import PlataformaCreate
from ofertas.services.plataforma_service import PlataformaService


class TestPlataformaService(unittest.TestCase):
    def setUp(self) -> None:
        self.repositorio = Mock()
        self.servico = PlataformaService(repository=self.repositorio)

    def test_criar_remove_espacos_extras(self) -> None:
        self.repositorio.buscar_por_codigo.return_value = None
        plataforma = Plataforma(
            id=1,
            codigo="mercado_livre",
            nome="Mercado Livre",
            status_plataforma=True,
        )
        self.repositorio.criar.return_value = plataforma

        dados = PlataformaCreate(
            codigo=" mercado_livre ",
            nome=" Mercado Livre ",
        )

        resultado = self.servico.criar(Mock(), dados)

        self.repositorio.criar.assert_called_once_with(
            unittest.mock.ANY,
            codigo="mercado_livre",
            nome="Mercado Livre",
            status_plataforma=True,
        )
        self.assertEqual(resultado.codigo, "mercado_livre")
        self.assertEqual(resultado.nome, "Mercado Livre")

    def test_criar_rejeita_codigo_duplicado(self) -> None:
        existente = Plataforma(
            id=1,
            codigo="mercado_livre",
            nome="Mercado Livre",
            status_plataforma=True,
        )
        self.repositorio.buscar_por_codigo.return_value = existente

        dados = PlataformaCreate(
            codigo="mercado_livre",
            nome="Mercado Livre",
        )

        with self.assertRaisesRegex(ValueError, "Já existe uma plataforma"):
            self.servico.criar(Mock(), dados)

        self.repositorio.criar.assert_not_called()

    def test_atualizar_status_rejeita_plataforma_inexistente(self) -> None:
        self.repositorio.buscar_por_codigo.return_value = None

        with self.assertRaisesRegex(LookupError, "não encontrada"):
            self.servico.atualizar_status(
                Mock(),
                "plataforma_inexistente",
                False,
            )

        self.repositorio.atualizar_status.assert_not_called()


if __name__ == "__main__":
    unittest.main()
