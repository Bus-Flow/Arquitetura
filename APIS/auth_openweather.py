import os

import requests
from dotenv import load_dotenv


load_dotenv()

TOKEN_WEATHER = os.getenv("TOKEN_WEATHER")

URL_OPENWEATHER = (
    "https://api.openweathermap.org/data/2.5/weather"
)


def consultar_clima():
    if not TOKEN_WEATHER:
        raise ValueError("TOKEN_WEATHER não encontrada no arquivo .env.")

    parametros = {
        "q": "Sao Paulo,BR",
        "appid": TOKEN_WEATHER.strip(),
        "units": "metric",
        "lang": "pt_br"
    }

    response = requests.get(
        URL_OPENWEATHER,
        params=parametros,
        timeout=30
    )

    response.raise_for_status()

    dados = response.json()

    descricao = dados["weather"][0]["description"]
    temperatura = dados["main"]["temp"]

    print("OpenWeather consultado com sucesso.")
    print(f"Clima: {descricao}")
    print(f"Temperatura: {temperatura} °C")

    return dados


if __name__ == "__main__":
    try:
        consultar_clima()

    except requests.HTTPError as erro:
        status = erro.response.status_code

        if status == 401:
            print("A chave do OpenWeather é inválida ou ainda não foi ativada.")
        else:
            print(f"Erro HTTP {status}: {erro}")

    except requests.RequestException as erro:
        print(f"Erro de comunicação com o OpenWeather: {erro}")

    except Exception as erro:
        print(f"Erro: {erro}")