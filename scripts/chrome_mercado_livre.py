"""Prepara o Chrome dedicado do projeto para gerar links afiliados do Mercado Livre.

O projeto usa um perfil próprio do Chrome (padrão: data/chrome_profile), separado
do seu Chrome pessoal. O login no Mercado Livre é feito uma única vez nesse
perfil; depois a API reutiliza a sessão salva.

Uso:
    python -m scripts.chrome_mercado_livre login      # abre o Chrome para você logar
    python -m scripts.chrome_mercado_livre verificar  # confere se a sessão está ativa
    python -m scripts.chrome_mercado_livre status     # mostra a configuração detectada
    python -m scripts.chrome_mercado_livre fechar     # fecha o Chrome do projeto
"""

import argparse
import logging
import sys

from ofertas.affiliates.mercado_livre_browser import (
    MercadoLivreBrowser,
    MercadoLivreBrowserError,
    MercadoLivreLoginRequiredError,
)


def _status(navegador: MercadoLivreBrowser) -> int:
    perfil = navegador.caminho_perfil()

    try:
        chrome = navegador._localizar_chrome()
    except FileNotFoundError as erro:
        chrome = f"NÃO ENCONTRADO ({erro})"

    print(f"Chrome:  {chrome}")
    print(f"Perfil:  {perfil} ({'existe' if perfil.exists() else 'será criado'})")
    print(f"CDP:     {navegador.cdp_url}")
    print(f"Aberto:  {'sim' if navegador.esta_aberto() else 'não'}")
    return 0


def _login(navegador: MercadoLivreBrowser) -> int:
    navegador.abrir()
    print(
        "Chrome do projeto aberto.\n"
        "1. Faça login no Mercado Livre na janela que abriu "
        "(conta com acesso ao programa de afiliados).\n"
        "2. Depois rode: make chrome-verificar\n"
        "Pode deixar o Chrome aberto: a API reutiliza esta janela."
    )
    return 0


def _verificar(navegador: MercadoLivreBrowser) -> int:
    try:
        resultado = navegador.verificar_sessao()
    except MercadoLivreLoginRequiredError:
        print("Sessão NÃO autenticada. Rode: make chrome-login")
        return 1
    except MercadoLivreBrowserError as erro:
        print(f"Não foi possível verificar a sessão: {erro}")
        return 2

    print(f"Sessão autenticada ({resultado['cookies']} cookies, {resultado['url']}).")
    return 0


def _fechar(navegador: MercadoLivreBrowser) -> int:
    if navegador.fechar():
        print("Chrome do projeto fechado.")
    else:
        print("O Chrome do projeto não estava aberto.")
    return 0


COMANDOS = {
    "status": _status,
    "login": _login,
    "verificar": _verificar,
    "fechar": _fechar,
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("comando", choices=COMANDOS)
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.WARNING, format="%(message)s")

    try:
        return COMANDOS[args.comando](MercadoLivreBrowser())
    except (FileNotFoundError, MercadoLivreBrowserError) as erro:
        print(f"Erro: {erro}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
