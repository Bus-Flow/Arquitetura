import requests

def testar_token_weather(token):
    cidade = "Sao Paulo,BR"
    url = f"https://api.openweathermap.org/data/2.5/weather?q={cidade}&appid={token}&units=metric&lang=pt_br"
    
    print("Testando comunicação com OpenWeather...")
    try:
        response = requests.get(url)
        dados = response.json()
        
        if response.status_code == 200:
            print("Chave do OpenWeather validada.")
            print(f"-> Clima em SP agora: {dados['weather'][0]['description']}, Temperatura: {dados['main']['temp']}°C")
        elif response.status_code == 401:
            print("Chave inválida ou ainda não ativada.")
        else:
            print(f"ERRO {response.status_code}: {dados.get('message', 'Desconhecido')}")
    except Exception as e:
        print(f"Erro de rede: {e}")

# Cole sua chave do OpenWeather aqui
TOKEN_WEATHER = "ff7cc980c0bc6823b91cbd0d1af58610"

testar_token_weather(TOKEN_WEATHER)