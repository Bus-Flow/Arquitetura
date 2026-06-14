import requests

def testar_token_sptrans(token):
    url = "http://api.olhovivo.sptrans.com.br/v2.1/Login/Autenticar"
    token_limpo = token.strip()
    
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    })
    
    print("Testando comunicação com a SPTrans...")
    try:
        response = session.post(url, params={'token': token_limpo}, headers={'Content-Length': '0'})
        
        if response.status_code == 200 and response.text.lower() == "true":
            print("A chave da SPTrans está ativa e funcionando.")
        else:
            print(f"A SPTrans rejeitou a chave. Status: {response.status_code} | Resposta: {response.text}")
    except Exception as e:
        print(f"Erro de rede: {e}")

TOKEN_SPTRANS = "07a60d55d2de72360de37d156be6824c972ecc0a95ec74e2bbba660c5c412d9d"

testar_token_sptrans(TOKEN_SPTRANS)