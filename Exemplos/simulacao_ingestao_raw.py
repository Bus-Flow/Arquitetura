import requests
import json
from datetime import datetime

class BusFlowClient:
    def __init__(self, token_sptrans, token_weather=None):
        self.token_sptrans = token_sptrans
        self.token_weather = token_weather
        
        self.base_url_sptrans = "http://api.olhovivo.sptrans.com.br/v2.1"
        self.session = requests.Session()
        
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })

    def autenticar(self):
        url = f"{self.base_url_sptrans}/Login/Autenticar?token={self.token_sptrans}"
        try:
            response = self.session.post(url, headers={"Content-Length": "0"})
            
            if response.status_code == 200 and response.text.lower() == "true":
                print("SPTrans: Autenticação realizada com sucesso!")
                return True
            else:
                print(f"SPTrans: Falha. Status: {response.status_code} | Resposta: {response.text}")
                return False
        except Exception as e:
            print(f"Erro ao conectar na SPTrans: {e}")
            return False

    def obter_posicoes_totais(self):
        """Traz a posição de TODOS os ônibus (O Payload para a ML)"""
        url = f"{self.base_url_sptrans}/Posicao"
        response = self.session.get(url)
        return response.json()

    def obter_clima_atual(self):
        """Busca os dados climáticos de São Paulo via OpenWeather"""
        if not self.token_weather:
            return {"erro": "Chave do OpenWeather não configurada no script."}
            
        cidade = "Sao Paulo,BR"
        url = f"https://api.openweathermap.org/data/2.5/weather?q={cidade}&appid={self.token_weather}&units=metric&lang=pt_br"
        
        response = requests.get(url)
        return response.json()

    def salvar_camada_raw(self, dados_frota, dados_clima):
        """Cria o arquivo JSON unificado para a gravação no Bucket S3"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        nome_arquivo = f"raw_busflow_{timestamp}.json"
        
        # O Payload final que vai para o Data Lake
        payload_raw = {
            "extracao_timestamp": timestamp,
            "clima": dados_clima,
            "sptrans": dados_frota
        }
        
        # Salvando o arquivo localmente
        with open(nome_arquivo, 'w', encoding='utf-8') as f:
            json.dump(payload_raw, f, ensure_ascii=False, indent=4)
            
        print(f"Arquivo gerado para a camada RAW: {nome_arquivo}")


# ==========================================
# EXECUÇÃO DO FLUXO 
# ==========================================

TOKEN_SPTRANS = "07a60d55d2de72360de37d156be6824c972ecc0a95ec74e2bbba660c5c412d9d"
TOKEN_WEATHER = "ff7cc980c0bc6823b91cbd0d1af58610" 

client = BusFlowClient(TOKEN_SPTRANS, TOKEN_WEATHER)

if client.autenticar():
    print("Coletando posições da frota...")
    dados_frota = client.obter_posicoes_totais()
    
    print("Coletando dados meteorológicos...")
    dados_clima = client.obter_clima_atual()
    
    print("Consolidando e enviando para RAW...")
    client.salvar_camada_raw(dados_frota, dados_clima)