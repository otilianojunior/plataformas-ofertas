import pytest

from ofertas.core.filtro_categoria import motivo_fora_da_categoria as motivo


@pytest.mark.parametrize(
    ("titulo", "termo"),
    [
        ("Headset Gamer Mchose V9 Turbo Wireless 200h Bateria", "headset mchose"),
        ("Logitech H390 Headset Com Fio Almofadas Super Confortáveis", "headset logitech"),
        ("Headset Gamer HyperX Cloud Flight S Wireless com Dongle USB", "headset hyperx"),
        ("Teclado Attack Shark X68 HE Magnetic", "teclado attack shark"),
        ("Mouse Gamer Sem Fio Attack Shark V6 25000dpi", "mouse attack shark"),
        ("Teclado Aula F75 Mecânico Gasket com Case de Alumínio", "teclado aula"),
        ("Qualquer título", None),
    ],
)
def test_produto_da_categoria_passa(titulo, termo):
    assert motivo(titulo, termo) is None


@pytest.mark.parametrize(
    ("titulo", "termo", "esperado"),
    [
        ("Headset Blackwire 8225 - 214408-01", "headset mchose", "marca"),
        ("Fone De Ouvido Gamer Sem Fio Astro A30", "headset logitech g", "marca"),
        ("Mouse Pad Gamer Corsair Mm300 Pro Medium", "mouse corsair", "mousepad"),
        ("Mousepad Gamer Hyperx Pulsefire Mat", "mouse hyperx", "mousepad"),
        ("Kit De Parafuso Para Teclado Akko Estabilizador", "teclado akko", "acessório"),
        ("Almofada Compatível Com Headset Redragon Lamia 2", "headset redragon", "acessório"),
        ("Hurricane 3 saco de armazenamento de fone Razer Barracuda", "headset razer", "acessório"),
        ("Kit Gamer Mchose Teclado Ace 60 Rgb Mouse L7", "teclado mchose", "kit"),
    ],
)
def test_produto_fora_da_categoria_e_descartado(titulo, termo, esperado):
    assert esperado in motivo(titulo, termo)
