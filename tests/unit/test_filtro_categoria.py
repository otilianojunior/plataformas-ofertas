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
        ("Apple iPhone 15 Pro Max (256 GB) - Titânio Natural", "iphone 15 pro max"),
        ("Smartphone Samsung Galaxy S25 Ultra 512GB com Capa", "samsung s25 ultra"),
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
        ("Capa Silicone Para iPhone 16 Com MagSafe", "iphone 16", "acessório"),
        ("Película de Vidro Samsung Galaxy S26", "samsung s26", "acessório"),
        ("Apple iPhone 15 (128 GB) - Preto", "iphone 15 pro max", "marca"),
    ],
)
def test_produto_fora_da_categoria_e_descartado(titulo, termo, esperado):
    assert esperado in motivo(titulo, termo)
