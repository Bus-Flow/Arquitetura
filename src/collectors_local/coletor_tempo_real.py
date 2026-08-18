import json
import time
from datetime import datetime
from pathlib import Path

import requests

from auth_openweather import consultar_clima
from auth_sptrans import autenticar_sptrans


INTERVALO_SEGUNDOS = 60

PASTA_ATUAL = Path(__file__).resolve().parent
PASTA_RAW = PASTA_ATUAL / "raw"

URL_POSICOES = (
    "http://api.olhovivo.sptrans.com.br/v2.1/Posicao"
)


def consultar_posicoes(sessao):
    response = sessao.get(
        URL_POSICOES,
        timeout=30
    )

    response.raise_for_status()

    return response.json()


def montar_dados_raw(dados_sptrans, dados_clima):
    return {
        "metadata": {
            "projeto": "BusFlow",
            "data_hora_coleta": datetime.now().astimezone().isoformat(),
            "fonte_transporte": "SPTrans Olho Vivo",
            "fonte_clima": "OpenWeather"
        },
        "clima": dados_clima,
        "sptrans": dados_sptrans
    }


def salvar_json(dados):
    PASTA_RAW.mkdir(parents=True, exist_ok=True)

    data_hora = datetime.now().strftime("%Y%m%d_%H%M%S")
    nome_arquivo = f"raw_busflow_{data_hora}.json"

    caminho = PASTA_RAW / nome_arquivo

    with caminho.open("w", encoding="utf-8") as arquivo:
        json.dump(
            dados,
            arquivo,
            ensure_ascii=False,
            indent=4
        )

    print(f"Arquivo salvo: {caminho}")


def executar_coleta(sessao):
    print("\nBuscando posições dos ônibus...")
    dados_sptrans = consultar_posicoes(sessao)

    print("Buscando condições climáticas...")
    dados_clima = consultar_clima()

    dados_raw = montar_dados_raw(
        dados_sptrans,
        dados_clima
    )

    salvar_json(dados_raw)

    linhas = dados_sptrans.get("l", [])

    quantidade_veiculos = sum(
        len(linha.get("vs", []))
        for linha in linhas
    )

    print(f"Linhas encontradas: {len(linhas)}")
    print(f"Veículos encontrados: {quantidade_veiculos}")
    print("Coleta concluída com sucesso.")


def iniciar_coletor():
    sessao = autenticar_sptrans()

    print(
        f"Coletor iniciado. "
        f"Uma coleta será feita a cada {INTERVALO_SEGUNDOS} segundos."
    )

    while True:
        inicio = time.monotonic()

        try:
            executar_coleta(sessao)

        except requests.HTTPError as erro:
            print(f"Erro HTTP durante a coleta: {erro}")
            print("Tentando autenticar novamente...")

            sessao.close()
            sessao = autenticar_sptrans()

        except requests.RequestException as erro:
            print(f"Erro de comunicação: {erro}")

        except Exception as erro:
            print(f"Erro inesperado: {erro}")

        duracao = time.monotonic() - inicio
        espera = max(0, INTERVALO_SEGUNDOS - duracao)

        print(f"Próxima coleta em {espera:.0f} segundos.")
        time.sleep(espera)


if __name__ == "__main__":
    try:
        iniciar_coletor()

    except KeyboardInterrupt:
        print("\nColetor encerrado pelo usuário.")

    except Exception as erro:
        print(f"Não foi possível iniciar o coletor: {erro}")    