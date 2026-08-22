import json
import os
from datetime import datetime
from pathlib import Path

import requests


# ==============================================================================
# CONFIGURAÇÕES
# ==============================================================================

HERE_API_KEY = os.getenv("HERE_API_KEY")

FLOW_URL = (
    "https://data.traffic.hereapi.com/v7/flow"
)

INCIDENTS_URL = (
    "https://data.traffic.hereapi.com/v7/incidents"
)


# Área aproximada do município de São Paulo.
#
# Formato exigido pela HERE:
# bbox:OESTE,SUL,LESTE,NORTE

BBOX_SAO_PAULO = (
    "bbox:"
    "-46.826,"
    "-24.008,"
    "-46.365,"
    "-23.356"
)


PASTA_ATUAL = Path(__file__).resolve().parent
PASTA_RAW = PASTA_ATUAL / "raw"


# ==============================================================================
# VALIDAÇÃO
# ==============================================================================

def validar_configuracoes():
    """
    Verifica se a chave da HERE está disponível
    nas variáveis de ambiente.
    """

    if not HERE_API_KEY:
        raise RuntimeError(
            "A variável de ambiente HERE_API_KEY "
            "não foi configurada."
        )


# ==============================================================================
# HERE TRAFFIC FLOW
# ==============================================================================

def consultar_fluxo(sessao):
    """
    Consulta o fluxo de trânsito em tempo real
    dentro da cidade de São Paulo.
    """

    params = {
        "in": BBOX_SAO_PAULO,
        "locationReferencing": "shape",
        "apiKey": HERE_API_KEY,
    }

    response = sessao.get(
        FLOW_URL,
        params=params,
        timeout=60,
    )

    response.raise_for_status()

    return response.json()


# ==============================================================================
# HERE TRAFFIC INCIDENTS
# ==============================================================================

def consultar_incidentes(sessao):
    """
    Consulta incidentes de trânsito em tempo real
    dentro da cidade de São Paulo.
    """

    params = {
        "in": BBOX_SAO_PAULO,
        "locationReferencing": "shape",
        "apiKey": HERE_API_KEY,
    }

    response = sessao.get(
        INCIDENTS_URL,
        params=params,
        timeout=60,
    )

    response.raise_for_status()

    return response.json()


# ==============================================================================
# CONVERSÃO DE VELOCIDADE
# ==============================================================================

def converter_ms_para_kmh(valor):
    """
    A HERE retorna speed e freeFlow em m/s.

    Converte o valor para km/h.
    """

    if valor is None:
        return None

    return round(
        valor * 3.6,
        2
    )


# ==============================================================================
# TRATAMENTO DO FLOW
# ==============================================================================

def tratar_fluxo(dados):
    """
    Extrai os campos necessários para o índice GT:

    - jamFactor
    - speed
    - freeFlow
    """

    trechos = []

    for item in dados.get(
        "results",
        []
    ):

        location = item.get(
            "location",
            {}
        )

        current_flow = item.get(
            "currentFlow",
            {}
        )

        speed_ms = current_flow.get(
            "speed"
        )

        free_flow_ms = current_flow.get(
            "freeFlow"
        )

        trecho = {
            "via":
                location.get(
                    "description"
                ),

            "comprimento_metros":
                location.get(
                    "length"
                ),

            "shape":
                location.get(
                    "shape"
                ),

            # ==========================
            # CAMPOS UTILIZADOS NO GT
            # ==========================

            "jamFactor":
                current_flow.get(
                    "jamFactor"
                ),

            "speed":
                converter_ms_para_kmh(
                    speed_ms
                ),

            "freeFlow":
                converter_ms_para_kmh(
                    free_flow_ms
                ),

            # ==========================
            # CAMPOS AUXILIARES
            # ==========================

            "confidence":
                current_flow.get(
                    "confidence"
                ),

            "traversability":
                current_flow.get(
                    "traversability"
                ),
        }

        trechos.append(
            trecho
        )

    return trechos


# ==============================================================================
# FUNÇÃO AUXILIAR PARA TEXTOS DA HERE
# ==============================================================================

def extrair_texto(valor):
    """
    Alguns textos da HERE podem ser retornados
    dentro de objetos contendo 'value'.
    """

    if isinstance(
        valor,
        dict
    ):
        return valor.get(
            "value"
        )

    return valor


# ==============================================================================
# TRATAMENTO DOS INCIDENTES
# ==============================================================================

def tratar_incidentes(dados):
    """
    Extrai principalmente:

    - type
    - criticality

    Esses campos também serão utilizados
    no cálculo do índice GT.
    """

    incidentes = []

    for item in dados.get(
        "results",
        []
    ):

        location = item.get(
            "location",
            {}
        )

        detalhes = item.get(
            "incidentDetails",
            {}
        )

        incidente = {
            "id":
                detalhes.get(
                    "id"
                ),

            "via":
                location.get(
                    "description"
                ),

            "comprimento_metros":
                location.get(
                    "length"
                ),

            "shape":
                location.get(
                    "shape"
                ),

            # ==========================
            # CAMPOS UTILIZADOS NO GT
            # ==========================

            "type":
                detalhes.get(
                    "type"
                ),

            "criticality":
                detalhes.get(
                    "criticality"
                ),

            # ==========================
            # CAMPOS AUXILIARES
            # ==========================

            "roadClosed":
                detalhes.get(
                    "roadClosed"
                ),

            "startTime":
                detalhes.get(
                    "startTime"
                ),

            "endTime":
                detalhes.get(
                    "endTime"
                ),

            "typeDescription":
                extrair_texto(
                    detalhes.get(
                        "typeDescription"
                    )
                ),

            "summary":
                extrair_texto(
                    detalhes.get(
                        "summary"
                    )
                ),

            "description":
                extrair_texto(
                    detalhes.get(
                        "description"
                    )
                ),
        }

        incidentes.append(
            incidente
        )

    return incidentes


# ==============================================================================
# MONTAGEM DOS DADOS
# ==============================================================================

def montar_dados(
    flow_raw,
    incidents_raw
):
    """
    Monta a estrutura final da coleta HERE.
    """

    fluxo = tratar_fluxo(
        flow_raw
    )

    incidentes = tratar_incidentes(
        incidents_raw
    )

    return {
        "metadata": {
            "projeto":
                "BusFlow",

            "data_hora_coleta":
                datetime.now()
                .astimezone()
                .isoformat(),

            "fonte":
                "HERE Traffic API v7",

            "area":
                "São Paulo - SP",

            "bbox":
                BBOX_SAO_PAULO,

            "source_updated_flow":
                flow_raw.get(
                    "sourceUpdated"
                ),

            "source_updated_incidents":
                incidents_raw.get(
                    "sourceUpdated"
                ),

            "quantidade_requisicoes":
                2,
        },

        "trafego": {
            "quantidade_trechos":
                len(fluxo),

            "trechos":
                fluxo,
        },

        "incidentes": {
            "quantidade_incidentes":
                len(incidentes),

            "dados":
                incidentes,
        },
    }


# ==============================================================================
# SALVAR JSON
# ==============================================================================

def salvar_json(dados):
    """
    Salva os dados coletados em um arquivo JSON.
    """

    PASTA_RAW.mkdir(
        parents=True,
        exist_ok=True
    )

    data_hora = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    nome_arquivo = (
        f"raw_here_{data_hora}.json"
    )

    caminho = (
        PASTA_RAW
        / nome_arquivo
    )

    with caminho.open(
        "w",
        encoding="utf-8"
    ) as arquivo:

        json.dump(
            dados,
            arquivo,
            ensure_ascii=False,
            indent=4
        )

    return caminho


# ==============================================================================
# EXECUTAR COLETA
# ==============================================================================

def executar_coleta():
    """
    Executa uma coleta completa da HERE.

    São realizadas duas requisições:

    1 - Traffic Flow
    2 - Traffic Incidents
    """

    validar_configuracoes()

    sessao = requests.Session()

    try:

        print()
        print(
            "===== HERE TRAFFIC API ====="
        )

        print()
        print(
            "Buscando fluxo de trânsito "
            "em São Paulo..."
        )

        flow_raw = consultar_fluxo(
            sessao
        )

        print(
            "Buscando incidentes de trânsito..."
        )

        incidents_raw = consultar_incidentes(
            sessao
        )

        print(
            "Tratando os dados..."
        )

        dados = montar_dados(
            flow_raw,
            incidents_raw
        )

        arquivo = salvar_json(
            dados
        )

        print()
        print(
            "===== COLETA FINALIZADA ====="
        )

        print(
            "Trechos encontrados:",
            dados["trafego"][
                "quantidade_trechos"
            ]
        )

        print(
            "Incidentes encontrados:",
            dados["incidentes"][
                "quantidade_incidentes"
            ]
        )

        print(
            "Requisições realizadas:",
            dados["metadata"][
                "quantidade_requisicoes"
            ]
        )

        print(
            "Arquivo salvo:",
            arquivo
        )

        # ======================================================
        # EXEMPLO DOS DADOS DE TRÁFEGO
        # ======================================================

        print()
        print(
            "===== AMOSTRA DE TRÁFEGO ====="
        )

        for trecho in (
            dados["trafego"]["trechos"][:5]
        ):

            print()
            print(
                "Via:",
                trecho["via"]
            )

            print(
                "Jam Factor:",
                trecho["jamFactor"]
            )

            print(
                "Velocidade atual:",
                trecho["speed"],
                "km/h"
            )

            print(
                "Velocidade livre:",
                trecho["freeFlow"],
                "km/h"
            )

        # ======================================================
        # EXEMPLO DOS INCIDENTES
        # ======================================================

        print()
        print(
            "===== AMOSTRA DE INCIDENTES ====="
        )

        for incidente in (
            dados["incidentes"]["dados"][:5]
        ):

            print()
            print(
                "Tipo:",
                incidente["type"]
            )

            print(
                "Criticidade:",
                incidente["criticality"]
            )

            print(
                "Via fechada:",
                incidente["roadClosed"]
            )

            print(
                "Descrição:",
                incidente["summary"]
            )

    finally:

        sessao.close()


# ==============================================================================
# MAIN
# ==============================================================================

if __name__ == "__main__":

    try:

        executar_coleta()

    except requests.HTTPError as erro:

        print()
        print(
            "Erro HTTP da HERE:",
            erro
        )

        if erro.response is not None:

            print(
                "Status:",
                erro.response.status_code
            )

            print(
                "Resposta:",
                erro.response.text
            )

    except requests.RequestException as erro:

        print(
            "Erro de comunicação "
            f"com a HERE: {erro}"
        )

    except Exception as erro:

        print(
            f"Erro inesperado: {erro}"
        )