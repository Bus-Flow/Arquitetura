import os

import requests
from dotenv import load_dotenv


load_dotenv()

TOKEN_SPTRANS = os.getenv("TOKEN_SPTRANS")

URL_AUTENTICACAO = (
    "http://api.olhovivo.sptrans.com.br/v2.1/Login/Autenticar"
)


def autenticar_sptrans():
    if not TOKEN_SPTRANS:
        raise ValueError("TOKEN_SPTRANS não encontrada no arquivo .env.")

    sessao = requests.Session()

    sessao.headers.update({
        "User-Agent": "BusFlow/1.0",
        "Accept": "application/json"
    })

    response = sessao.post(
        URL_AUTENTICACAO,
        params={"token": TOKEN_SPTRANS.strip()},
        headers={"Content-Length": "0"},
        timeout=30
    )

    response.raise_for_status()

    if response.text.strip().lower() != "true":
        raise RuntimeError(
            f"A SPTrans recusou a autenticação: {response.text}"
        )

    print("Autenticação na SPTrans realizada com sucesso.")

    return sessao


if __name__ == "__main__":
    try:
        sessao_sptrans = autenticar_sptrans()
        sessao_sptrans.close()

    except requests.RequestException as erro:
        print(f"Erro de comunicação com a SPTrans: {erro}")

    except Exception as erro:
        print(f"Erro: {erro}")