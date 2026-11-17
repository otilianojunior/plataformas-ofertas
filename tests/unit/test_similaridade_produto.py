"""Casos reais de títulos publicados (Mercado Livre e Shopee)."""

import pytest

from ofertas.core.similaridade_produto import mesmo_produto


MESMO = [
    # mesmo anúncio em outra listagem / outra cor
    ("Celular Samsung Galaxy A17 Com Ia, 256gb, 8gb Ram, Câm De 50mp, Tela De 6.7 , Nfc, Ip54 - Azul",
     "Celular Samsung Galaxy A17 Com Ia, 256gb, 8gb Ram, Câm De 50mp, Tela De 6.7 , Nfc, Ip54 - Preto"),
    ("Smart TV HD 32\" LG LB650 AI 2026 Processador α5 Ger9 HDR10 Xbox Bluetooth Wi-Fi AI Search Googl",
     "Smart TV HD 32\" LG LB650 AI 2026 Processador α5 Ger9 HDR10 Xbox Bluetooth Wi-Fi AI Search Googl"),
    ("Water Cooler Kalkan Aura LCD 240mm ARGB Gamer Preto", "Water Cooler Kalkan Aura LCD 240mm ARGB Gamer"),
    # títulos de lojas diferentes para o mesmo modelo
    ("Smart Tv Aoc Dled 32 Wi-fi Roku Tv Quad Core 32s5155/78g",
     "Smart TV AOC 32\" Roku DLED 32S5155 Wi-Fi Original Envio Imediato"),
    ("Monitor AOC 24\" 100Hz 1ms Gaming HDMI 24B35HM2", "Monitor Gamer AOC 24B35HM2 24 Polegadas 100hz"),
    ("SSD Kingston A400 240GB SATA 3", "SSD KINGSTON 240GB A400 INTERNO SATA 3 6GB/S Original"),
    ("Fan Pcyes Para Gabinete Sangue Frio 3 Black Vulcan 120mm",
     "Fan Pcyes Para Gabinete Sangue Frio 3 Black Vulcan 120mm"),
    ("Monitor gamer Aoc Série B30 21.5'' Full Hd Gaming 120hz 1ms 22b30hm23 cor preto",
     "Monitor Gamer AOC 22\" Full HD Gaming 120Hz 1ms 22B30HM23"),
    ("Monitor LED 20 Brazil PC 20WR - 1600x900, 75Hz, 5ms - HDMI/VGA - Preto",
     "Monitor LED 20\" HD+ Brasil PC 20WR, 1600x900, 75Hz, HDMI/VGA"),
    ("Placa Mãe Asus Tuf Gaming B550m-plus Ddr4 AMD Am4 mATX RGB",
     "Placa-mãe ASUS TUF Gaming B550m-plus AMD AM4 Matx DDR4 Preto"),
    ("Monitor Gamer AOC AGON G50 24\" 144Hz 0,5ms IPS HDR10 G-SYNC 24G50F Preto",
     "Monitor Gamer AOC 23,8\" Full HD 144Hz Agon G50 IPS 0,5ms 24G50F/57 HDMI"),
    ("Kit Ventoinhas Pichau Ventus Nx, Argb, 5x120mm, Preto",
     "Kit Ventoinhas Pichau Ventus NX, ARGB, 5x120mm, Preto, PCH-VTNX5-BK01"),
]

DIFERENTE = [
    ("Celular Samsung Galaxy S25 Ultra 5g, 256gb, 12gb, Câm. Quád. - Titanium Silverblue",
     "Samsung Galaxy S25 5G, 256GB, 12GB, Câmera Tripla - Azul marinho"),
    ("Ventoinha Pichau Ventus Nx, Argb, 120mm, Preto, Pch-vtn-bk01",
     "Ventoinha Pichau Ventus NX Reverse ARGB 120mm Preto PCH-VTNR-BK01"),
    ("Apple iPhone 16 (256 GB) - Rosa - Distribuidor Autorizado",
     "iPhone 16e (128 GB) - Preto - Distribuidor Autorizado"),
    ("Smartphone Motorola Moto G06 - 256gb 4gb Ram e Camera 50mp",
     "Smartphone Motorola Moto G86 5G Tela 6.7 pOLED 256GB 8GB RAM Câmera 50MP"),
    ("Smart Tv Aoc Dled 32 Wi-fi Roku Tv Quad Core 32s5155/78g",
     "Smart Tv 43 Aoc Led Roku Full Hd Wi-fi 60hz Hdmi Usb 43s5155/78g"),
    ("Monitor Gamer Samsung 27\" FHD,120 Hz, HDMI, Preto, S3",
     "Monitor Gamer Samsung Odyssey G5, 32 ,qhd, 165hz,1ms,hdmi,dp Preto"),
    ("Headset Razer Blackshark V2 X", "Headset Razer Blackshark V2 Wireless"),
    ("SSD Kingston A400 240GB", "SSD Kingston A400 480GB"),
    ("Mouse Gamer Logitech G203", "Teclado Mecânico Gamer Redragon Kumara"),
    ("LG UltraGear Monitor Gamer 27\" IPS, 144Hz Nativo, 1ms (MBR), Full HD (1920x1080)",
     "Monitor Gamer LG UltraGear 24”IPS Full HD 180Hz 1ms"),
    ("Smart TV Philips 32 polegadas QLED HD Wi-Fi HDR10 Dolby Áudio 32PQG6921/78",
     "Smart TV Philips 43 polegadas QLED Full HD Wi-Fi HDR10 Dolby Áudio 43PGQ6921/78"),
    ("Smartphone Motorola Moto G06 - 256gb 4gb Ram e Camera 50mp",
     "Smartphone Motorola Moto G06 4G 6.9Pol 128GB 4GB Câmera 50MP"),
    ("Placa Mãe Asus Tuf Gaming B550m-plus Ddr4 AMD Am4 mATX RGB",
     "Placa-Mãe ASUS TUF GAMING A520M-PLUS WIFI, AMD AM4, RGB, mATX, DDR4"),
    ("Teclado Titanis USB com Fio ABNT2 Ergonômico para Computador",
     "Teclado, Mouse ou Kit Teclado + Mouse USB Com Fio ABNT2 Ergonômico Preto"),
    ("Kit Ventoinhas Pichau Ventus Nx, Argb, 5x120mm, Preto",
     "Kit Ventoinhas TGT Striker, Rainbow, 5x120mm, TGT-STK5-BLRBW"),
    ("Cpu Cooler 120mm Led Intel X79 X99 X299 Lga 1200 1151 2011",
     "Suporte Para Cooler Intel Socket Lga 2011 Para X79 X99 X299"),
]


@pytest.mark.parametrize(("a", "b"), MESMO)
def test_reconhece_o_mesmo_produto(a, b):
    assert mesmo_produto(a, b)
    assert mesmo_produto(b, a)


@pytest.mark.parametrize(("a", "b"), DIFERENTE)
def test_distingue_produtos_diferentes(a, b):
    assert not mesmo_produto(a, b)
    assert not mesmo_produto(b, a)
