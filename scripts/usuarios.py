"""Usuários do painel. A senha é pedida no terminal e não aparece na tela.

Uso:
    python -m scripts.usuarios admin [login]   # cria o admin master (padrão: admin)
    python -m scripts.usuarios senha <login>   # troca a senha (e reativa o usuário)
"""

import argparse
import getpass
import sys

from ofertas.db.session import SessionLocal
from ofertas.services.usuario_service import UsuarioService


def _pedir_senha() -> str:
    senha = getpass.getpass("Senha (mín. 8 caracteres): ")
    if senha != getpass.getpass("Repita a senha: "):
        sys.exit("As senhas não conferem.")
    return senha


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    comandos = parser.add_subparsers(dest="comando", required=True)
    admin = comandos.add_parser("admin", help="cria o usuário administrador master")
    admin.add_argument("login", nargs="?", default="admin")
    senha = comandos.add_parser("senha", help="troca a senha de um usuário")
    senha.add_argument("login")
    args = parser.parse_args()

    servico = UsuarioService()

    with SessionLocal() as session:
        try:
            if args.comando == "admin":
                nome = input("Nome (Enter = Administrador): ").strip() or "Administrador"
                usuario = servico.criar(
                    session, login=args.login, nome=nome, senha=_pedir_senha(), perfil="admin"
                )
            else:
                usuario = servico.alterar_senha(session, args.login, _pedir_senha())
            session.commit()
        except (ValueError, LookupError) as exc:
            session.rollback()
            sys.exit(f"Erro: {exc}")

    print(f"Pronto: '{usuario.login}' ({usuario.perfil}). Entre em http://127.0.0.1:8000/painel")


if __name__ == "__main__":
    main()
