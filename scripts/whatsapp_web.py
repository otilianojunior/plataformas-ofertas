"""Prepara e testa o WhatsApp Web usado para publicar nos grupos.

Integração NÃO oficial: o número pode ser restringido ou banido pelo WhatsApp.
Use um número que você aceite perder e só nos seus grupos.

Uso:
    python -m scripts.whatsapp_web login                  # abre o Chrome para ler o QR Code
    python -m scripts.whatsapp_web verificar              # a sessão está conectada?
    python -m scripts.whatsapp_web status                 # configuração detectada
    python -m scripts.whatsapp_web fechar                 # fecha o Chrome do WhatsApp
    python -m scripts.whatsapp_web teste "Nome do grupo"  # prepara uma mensagem SEM enviar
    python -m scripts.whatsapp_web teste "Nome do grupo" --enviar  # envia de verdade
"""

import argparse
import logging
import sys

from ofertas.publishers.whatsapp_web import (
    WhatsAppWebBrowser,
    WhatsAppWebClient,
    WhatsAppWebError,
)


MENSAGEM_TESTE = (
    "*Teste do Plataformas de Ofertas*\n"
    "\n"
    "Se você está lendo isto, a publicação pelo WhatsApp Web funciona. ✅"
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("comando", choices=["login", "verificar", "status", "fechar", "teste"])
    parser.add_argument("grupo", nargs="?", help="nome exato do grupo (comando teste)")
    parser.add_argument("--enviar", action="store_true", help="envia de verdade (teste)")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    for biblioteca in ("httpx", "httpcore"):
        logging.getLogger(biblioteca).setLevel(logging.WARNING)

    navegador = WhatsAppWebBrowser()
    cliente = WhatsAppWebClient(browser=navegador)

    try:
        if args.comando == "status":
            print(f"Perfil:  {navegador.caminho_perfil()}")
            print(f"CDP:     {navegador.cdp_url}")
            print(f"Aberto:  {'sim' if navegador.esta_aberto() else 'não'}")
            print(f"Limites: {cliente.settings.whatsapp_intervalo_minimo_segundos}s entre "
                  f"mensagens, {cliente.settings.whatsapp_limite_diario} por dia")
            return 0

        if args.comando == "login":
            navegador.abrir()
            print("Chrome do WhatsApp aberto em web.whatsapp.com.\n"
                  "No celular: WhatsApp > Dispositivos conectados > Conectar dispositivo,\n"
                  "e leia o QR Code. Depois rode: make whatsapp-verificar")
            return 0

        if args.comando == "verificar":
            estado = cliente.status()
            print(estado["detalhe"])
            return 0 if estado["conectado"] else 1

        if args.comando == "fechar":
            print("Chrome do WhatsApp fechado." if navegador.fechar() else "Já estava fechado.")
            return 0

        if not args.grupo:
            parser.error("informe o nome do grupo: teste \"Nome do grupo\"")

        cliente.enviar(args.grupo, MENSAGEM_TESTE, confirmar=args.enviar)
        print("Mensagem enviada." if args.enviar else
              "Mensagem preparada no grupo, SEM enviar. Confira a janela do Chrome\n"
              "(apague o texto se quiser). Para enviar de verdade, use --enviar.")
        return 0

    except (WhatsAppWebError, FileNotFoundError) as erro:
        print(f"Erro: {erro}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
