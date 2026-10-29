from cryptography.fernet import Fernet

from ofertas.core.config import get_settings


def criptografar_credencial(valor: str) -> str:
    if not valor:
        raise ValueError("A credencial não pode ser vazia.")

    settings = get_settings()
    chave = settings.credential_encryption_key.encode("utf-8")

    return Fernet(chave).encrypt(valor.encode("utf-8")).decode("utf-8")


def descriptografar_credencial(valor_criptografado: str) -> str:
    if not valor_criptografado:
        raise ValueError("A credencial criptografada não pode ser vazia.")

    settings = get_settings()
    chave = settings.credential_encryption_key.encode("utf-8")

    return Fernet(chave).decrypt(
        valor_criptografado.encode("utf-8")
    ).decode("utf-8")
