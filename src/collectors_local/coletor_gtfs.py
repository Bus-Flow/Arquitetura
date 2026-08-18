import os
import zipfile
from datetime import datetime
from io import BytesIO
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv


load_dotenv()


LOGIN_URL = (
    "https://www.sptrans.com.br/"
    "desenvolvedores/login-desenvolvedores"
)

PERFIL_URL = (
    "https://www.sptrans.com.br/"
    "desenvolvedores/perfil-desenvolvedor/"
)

DOWNLOAD_URL = (
    "https://www.sptrans.com.br/"
    "umbraco/Surface/PerfilDesenvolvedor/"
    "BaixarGTFS?memberName=_sptrans"
)

SPTRANS_USERNAME = os.getenv("SPTRANS_USERNAME")
SPTRANS_PASSWORD = os.getenv("SPTRANS_PASSWORD")


def validar_variaveis_ambiente() -> None:
    """Verifica se usuário e senha foram preenchidos no .env."""

    variaveis = {
        "SPTRANS_USERNAME": SPTRANS_USERNAME,
        "SPTRANS_PASSWORD": SPTRANS_PASSWORD,
    }

    ausentes = [
        nome
        for nome, valor in variaveis.items()
        if not valor
    ]

    if ausentes:
        raise ValueError(
            "Variáveis de ambiente ausentes: "
            + ", ".join(ausentes)
        )


def criar_sessao() -> requests.Session:
    """Cria uma sessão HTTP que mantém os cookies do login."""

    session = requests.Session()

    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/150.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
    })

    return session


def obter_token_ufprt(session: requests.Session) -> str:
    """Abre a página de login e extrai o token de segurança ufprt."""

    response = session.get(
        LOGIN_URL,
        timeout=30,
    )

    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    campo_token = soup.find(
        "input",
        attrs={"name": "ufprt"},
    )

    if not campo_token:
        raise RuntimeError(
            "O campo ufprt não foi encontrado na página de login."
        )

    token = campo_token.get("value")

    if not token:
        raise RuntimeError(
            "O campo ufprt foi encontrado, mas está sem valor."
        )

    return token


def fazer_login(
    session: requests.Session,
    token_ufprt: str,
) -> None:
    """Realiza o login no portal de desenvolvedores da SPTrans."""

    dados_login = {
        "loginModel.Username": SPTRANS_USERNAME,
        "loginModel.Password": SPTRANS_PASSWORD,
        "ufprt": token_ufprt,
    }

    response = session.post(
        LOGIN_URL,
        data=dados_login,
        headers={
            "Referer": LOGIN_URL,
            "Origin": "https://www.sptrans.com.br",
        },
        timeout=30,
        allow_redirects=True,
    )

    response.raise_for_status()

    url_final = response.url.lower()
    conteudo = response.text.lower()

    login_confirmado = (
        "perfil-desenvolvedor" in url_final
        or "perfil desenvolvedor" in conteudo
    )

    if not login_confirmado:
        raise RuntimeError(
            "Não foi possível confirmar o login na SPTrans. "
            "Verifique o usuário e a senha."
        )

    print("Login realizado com sucesso.")


def baixar_gtfs(session: requests.Session) -> bytes:
    """Baixa o arquivo ZIP do GTFS usando a sessão autenticada."""

    response = session.get(
        DOWNLOAD_URL,
        headers={
            "Referer": PERFIL_URL,
        },
        timeout=120,
    )

    response.raise_for_status()

    conteudo = response.content

    if not conteudo:
        raise RuntimeError(
            "O download foi concluído, mas o arquivo está vazio."
        )

    if not zipfile.is_zipfile(BytesIO(conteudo)):
        content_type = response.headers.get(
            "Content-Type",
            "desconhecido",
        )

        raise RuntimeError(
            "O conteúdo baixado não é um ZIP válido. "
            f"Content-Type recebido: {content_type}"
        )

    tamanho_mb = len(conteudo) / (1024 * 1024)

    print(
        f"GTFS baixado com sucesso: {tamanho_mb:.2f} MB."
    )

    return conteudo


def salvar_copia_local(
    conteudo: bytes,
    nome_arquivo: str,
) -> Path:
    """Salva o arquivo ZIP localmente."""

    diretorio = Path("data/raw/gtfs")

    diretorio.mkdir(
        parents=True,
        exist_ok=True,
    )

    caminho = diretorio / nome_arquivo

    caminho.write_bytes(conteudo)

    print(f"Arquivo salvo em: {caminho.resolve()}")

    return caminho


def executar_coleta() -> None:
    """Executa o login, download e salvamento local do GTFS."""

    validar_variaveis_ambiente()

    agora = datetime.now()

    nome_arquivo = (
        f"moovitbr_gtfs_{agora:%Y%m%d_%H%M%S}.zip"
    )

    session = criar_sessao()

    try:
        print("Buscando token de autenticação...")
        token = obter_token_ufprt(session)

        print("Realizando login na SPTrans...")
        fazer_login(session, token)

        print("Baixando arquivo GTFS...")
        arquivo_gtfs = baixar_gtfs(session)

        salvar_copia_local(
            arquivo_gtfs,
            nome_arquivo,
        )

        print("Coleta finalizada com sucesso.")

    finally:
        session.close()


if __name__ == "__main__":
    try:
        executar_coleta()

    except requests.RequestException as erro:
        print(f"Erro de comunicação com a SPTrans: {erro}")

    except Exception as erro:
        print(f"Erro durante a coleta: {erro}")