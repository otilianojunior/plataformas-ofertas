"""Senhas do painel (hash scrypt) e tokens de sessão (Fernet).

O token é cifrado e assinado com a mesma CREDENTIAL_ENCRYPTION_KEY das
credenciais; trocar a chave derruba todas as sessões. A senha nunca é
cifrada de forma reversível: guardamos só o hash com sal.
"""

import base64
import hashlib
import hmac
import json
import secrets

from cryptography.fernet import Fernet, InvalidToken

from ofertas.core.config import get_settings


# Custo do scrypt (~16 MiB de memória por verificação).
_SCRYPT_N = 2**14
_SCRYPT_R = 8
_SCRYPT_P = 1
_TAMANHO_HASH = 32

SENHA_TAMANHO_MINIMO = 8


def _b64(dados: bytes) -> str:
    return base64.b64encode(dados).decode("ascii")


def _scrypt(senha: str, sal: bytes, n: int, r: int, p: int) -> bytes:
    return hashlib.scrypt(
        senha.encode("utf-8"),
        salt=sal,
        n=n,
        r=r,
        p=p,
        maxmem=64 * 1024 * 1024,
        dklen=_TAMANHO_HASH,
    )


def gerar_hash_senha(senha: str) -> str:
    if len(senha) < SENHA_TAMANHO_MINIMO:
        raise ValueError(
            f"A senha deve ter ao menos {SENHA_TAMANHO_MINIMO} caracteres."
        )

    sal = secrets.token_bytes(16)
    resumo = _scrypt(senha, sal, _SCRYPT_N, _SCRYPT_R, _SCRYPT_P)

    return f"scrypt${_SCRYPT_N}${_SCRYPT_R}${_SCRYPT_P}${_b64(sal)}${_b64(resumo)}"


def verificar_senha(senha: str, senha_hash: str) -> bool:
    try:
        algoritmo, n, r, p, sal, resumo = senha_hash.split("$")
        if algoritmo != "scrypt":
            return False
        calculado = _scrypt(
            senha, base64.b64decode(sal), int(n), int(r), int(p)
        )
    except (ValueError, TypeError):
        return False

    return hmac.compare_digest(calculado, base64.b64decode(resumo))


# Hash de uma senha qualquer: login inexistente gasta o mesmo tempo que
# senha errada, sem revelar quais logins existem.
HASH_FICTICIO = gerar_hash_senha(secrets.token_urlsafe(16))


def _fernet() -> Fernet:
    return Fernet(get_settings().credential_encryption_key.encode("utf-8"))


def _carimbo(senha_hash: str) -> str:
    # Trocar a senha invalida as sessões abertas.
    return hashlib.sha256(senha_hash.encode("utf-8")).hexdigest()[:16]


def gerar_token_sessao(usuario_id: int, senha_hash: str) -> str:
    conteudo = json.dumps({"uid": usuario_id, "sh": _carimbo(senha_hash)})
    return _fernet().encrypt(conteudo.encode("utf-8")).decode("ascii")


def ler_token_sessao(token: str) -> tuple[int, str] | None:
    """Devolve (usuario_id, carimbo da senha) ou None se inválido/expirado."""

    try:
        bruto = _fernet().decrypt(
            token.encode("ascii"),
            ttl=get_settings().sessao_duracao_horas * 3600,
        )
        dados = json.loads(bruto)
        return int(dados["uid"]), str(dados["sh"])
    except (InvalidToken, ValueError, KeyError, TypeError, UnicodeError):
        return None


def token_confere_com_senha(carimbo: str, senha_hash: str) -> bool:
    return hmac.compare_digest(carimbo, _carimbo(senha_hash))
