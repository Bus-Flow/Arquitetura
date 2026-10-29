# 📊 Guia Oficial: Acesso, Configuração e Dashboards no Grafana (BusFlow)

Este guia foi elaborado sob medida para a configuração do **Grafana** na infraestrutura do projeto **BusFlow**, utilizando os dados reais provisionados na AWS. 

> 💡 **Informação Importante:** Você **NÃO** precisa instalar o Grafana manualmente! Ele já foi baixado, configurado e iniciado de forma 100% automática durante a criação da máquina na AWS via script de inicialização (`user_data`).

---

## 📌 1. Dados Reais da Infraestrutura

Guarde estas informações, você vai usá-las nos próximos passos:

* **URL Direta do Grafana (Navegador):** `http://18.207.117.141:3000`
* **IP da sua Máquina EC2 (Grafana):** `18.207.117.141`
* **Usuário SSH da Máquina:** `ec2-user`
* **Host do Banco de Dados (RDS PostgreSQL):** `db-busflow.cf0bvo08d8bp.us-east-1.rds.amazonaws.com`
* **Porta do Banco:** `5432`
* **Nome do Banco:** `busflowdb`
* **Usuário do Banco:** `postgres`
* *(Para referência: a outra EC2 no IP `54.226.189.184` é a que roda o modelo de Machine Learning).*

---

## 💻 2. Acesso à EC2 via Windows (PowerShell)

Como você usa Windows e não acessa o console da AWS pelo navegador, a conexão será feita pelo terminal do Windows utilizando a chave privada `terraform_key.pem` que você recebeu.

### Passo 2.1: Salvar a chave `.pem`
1. Crie uma pasta de fácil acesso (por exemplo, `C:\BusFlow` ou na sua pasta `Downloads`).
2. Cole o arquivo `terraform_key.pem` nessa pasta.

### Passo 2.2: Ajustar a permissão da chave no Windows
O Windows costuma bloquear chaves SSH que estejam com permissões abertas demais. Para evitar o erro `UNPROTECTED PRIVATE KEY FILE`:
1. Abra o **PowerShell** no Windows.
2. Navegue até a pasta onde está a chave:
   ```powershell
   cd C:\BusFlow
   ```
3. Execute estes dois comandos para ajustar as permissões:
   ```powershell
   icacls .\terraform_key.pem /inheritance:r
   icacls .\terraform_key.pem /grant:r "$($env:USERNAME):(R)"
   ```

### Passo 2.3: Conectar via SSH e abrir o Túnel para o Grafana
Recomendamos conectar utilizando **Túnel SSH (Port Forwarding)** com a flag `-L 3000:localhost:3000`. Isso garante que o tráfego do Grafana passe direto pelo SSH, contornando bloqueios de firewall da sua rede/VPN e sem depender de regras extras de portas no Security Group:

```powershell
ssh -i .\busflow_key.pem -L 3000:localhost:3000 ec2-user@18.207.117.141
```
*(Se perguntar `Are you sure you want to continue connecting (yes/no)?`, digite `yes` e dê Enter).*

Pronto! Você verá o logo do **Amazon Linux 2023** e estará dentro do terminal da EC2.

---

## 🔍 3. Validando que o Grafana já está Rodando

Dentro do terminal preto da EC2, execute:

```bash
sudo systemctl status grafana-server
```

Você verá um texto com **`Active: active (running)` em verde**, confirmando que o script automático já fez toda a instalação e colocou o servidor no ar!
*(Para sair da visualização do status, basta apertar a letra `q` no teclado).*

---

## 🌐 4. Primeiro Acesso à Interface Web do Grafana

Agora que o túnel SSH está ativo no seu terminal:

1. Abra o navegador no seu computador (Chrome, Edge ou Firefox).
2. Acesse o endereço local:
   ```text
   http://localhost:3000
   ```
   *(Ou diretamente pelo IP público `http://18.207.117.141:3000`, caso a porta 3000 esteja liberada na sua rede).*
3. Na tela de login:
   * **Email or username:** `admin`
   * **Password:** `admin`
4. O Grafana solicitará que você defina uma nova senha. Escolha uma senha segura e confirme.

---

## 🔌 5. Conectando o Grafana ao Banco RDS PostgreSQL

Agora vamos conectar o Grafana ao banco do BusFlow para buscar os dados dos ônibus em tempo real:

1. No menu lateral esquerdo do Grafana, clique em **Connections** → **Data sources**.
2. Clique no botão azul **Add data source** no canto superior direito.
3. Na caixa de pesquisa, digite **PostgreSQL** e clique no card correspondente.
4. Preencha os campos com as informações exatas abaixo:
   * **Host:** `db-busflow.cf0bvo08d8bp.us-east-1.rds.amazonaws.com:5432`
   * **Database name:** `busflowdb`
   * **Username:** `postgres`
   * **Password:** *(digite a senha do banco repassada pela equipe)*
   * **TLS/SSL Mode:** selecione `disable` (ou `require`)
   * **Version:** selecione `14` (ou mais recente)
5. Role a página até o rodapé e clique no botão **Save & test**.
6. Uma notificação verde deve surgir na tela: **`Database Connection OK`**.

---

## 📊 6. Criando o Dashboard e os Painéis (Queries SQL Prontas)

Com o banco conectado, vamos criar as telas operacionais!

1. No menu lateral esquerdo, clique em **Dashboards** → botão **New** (no canto superior direito) → **New Dashboard**.
2. Clique em **+ Add visualization**.
3. Selecione a fonte de dados **PostgreSQL** que acabamos de cadastrar.
4. Na parte inferior da tela, localize o editor de consultas e alterne para o modo **Code** (Editor SQL direto).
5. Cole as consultas abaixo para cada painel que você desejar criar:

---

### Painel 1: Donut de Status Geral da Frota
* **Visualização (menu do lado direito):** Selecione **Pie chart**
* **Título do Painel (Title):** `Status Geral da Frota`
* **Consulta SQL:**
  ```sql
  SELECT 
      status_linha AS metric, 
      COUNT(*) AS total 
  FROM v_grafana_status_linhas 
  GROUP BY status_linha;
  ```
* **Mapeamento de Cores sugerido:**
  * `Estabilizado` ➔ Verde (#73BF69)
  * `Risco de Gargalo` ➔ Amarelo (#FADE2A)
  * `Gargalo` ➔ Vermelho (#F2495C)

---

### Painel 2: Circulação dos Veículos na Régua de Paradas (1 a N)
* **Visualização:** Selecione **Table** ou **Bar Gauge**
* **Título do Painel:** `Circulação da Frota na Régua de Paradas`
* **Consulta SQL:**
  ```sql
  SELECT 
      prefixo_carro AS "Veículo",
      ponto_parada_seq AS "Parada Atual (Seq)",
      status_carro AS "Status",
      ROUND(aderencia_individual::numeric, 2) AS "Aderência"
  FROM v_grafana_circulacao_carros
  ORDER BY ponto_parada_seq ASC;
  ```

---

### Painel 3: Cards com Recomendações e Diagnósticos de ML (Random Forest)
* **Visualização:** Selecione **Table**
* **Título do Painel:** `Diagnósticos e Alertas Preditivos (Random Forest)`
* **Consulta SQL:**
  ```sql
  SELECT 
      linha_codigo AS "Linha",
      status_previsto AS "Diagnóstico Previsto",
      deficit_veiculos AS "Déficit Previsto",
      acao_necessaria AS "Ação Recomendada",
      justificativa AS "Causa Raiz Identificada"
  FROM fato_previsao_ml 
  WHERE alerta_ativo = TRUE
  ORDER BY timestamp_previsao DESC
  LIMIT 10;
  ```

---

### Painel 4: Curva Temporal de Demanda Real vs. Demanda Ideal
* **Visualização:** Selecione **Time series**
* **Título do Painel:** `Demanda Real vs Ideal (Frota Ativa)`
* **Consulta SQL:**
  ```sql
  SELECT 
      timestamp_registro AS time, 
      frota_ativa_real AS "Demanda Real", 
      frota_necessaria_dfi AS "Demanda Ideal" 
  FROM fato_linha_operacao 
  ORDER BY time ASC;
  ```

---

### Painel 5: Aderência ao Cronograma por Linha (%)
* **Visualização:** Selecione **Bar chart**
* **Título do Painel:** `Aderência ao Cronograma por Linha (%)`
* **Consulta SQL:**
  ```sql
  SELECT 
      itinerario AS "Linha / Sentido", 
      aderencia_cronograma_pct AS "Aderência %" 
  FROM v_grafana_status_linhas 
  ORDER BY aderencia_cronograma_pct ASC;
  ```

---

### Painel 6: Auditoria e Backtesting do Modelo de IA
* **Visualização:** Selecione **Pie chart** ou **Stat**
* **Título do Painel:** `Backtesting Automatizado de Previsões`
* **Consulta SQL:**
  ```sql
  SELECT 
      resultado_validacao AS metric, 
      COUNT(*) AS total 
  FROM v_grafana_validacao_ml 
  GROUP BY resultado_validacao;
  ```

---

## 🛠️ 7. Resolução de Problemas no Windows (FAQ)

| Problema | Causa | O que fazer |
| :--- | :--- | :--- |
| **`UNPROTECTED PRIVATE KEY FILE` no terminal** | O Windows não permite rodar SSH com chaves que outros usuários possam ler. | Rode os dois comandos do item 2.2 (`icacls`) no PowerShell antes de executar o `ssh`. |
| **Navegador não abre `http://18.207.117.141:3000`** | O navegador pode ter colocado `https://` automaticamente. | Garanta que o link comece com **`http://`** (sem o "s"). |
| **Erro "Connection timed out" no PostgreSQL** | O Host foi preenchido com `https://` ou sem a porta `:5432`. | No campo Host, digite exatamente: `db-busflow.cf0bvo08d8bp.us-east-1.rds.amazonaws.com:5432`. |
| **Erro "password authentication failed"** | Senha incorreta digitada. | Confirme a senha do banco configurada pela equipe no arquivo `terraform.tfvars`. |
