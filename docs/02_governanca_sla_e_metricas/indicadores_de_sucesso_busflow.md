# Indicadores de Sucesso & Framework de OKRs — Projeto BusFlow

**Documento Prático para Validação com a Equipe**  
**Projeto:** BusFlow — Inteligência Operacional de Transporte Público  
**Estrutura:** Cada etapa do pipeline contém seu **OKR Estratégico (Objetivo + KRs)** acompanhado da **Tabela Operacional de Métricas (com régua de Falha, Regular e Sucesso)**.

---

## Como ler este documento
1. **Objetivo (O):** O direcionador estratégico de valor da etapa (o que queremos alcançar).
2. **Resultados-Chave (KRs):** As metas quantitativas para comprovar que o objetivo foi atingido (derivadas da coluna de sucesso).
3. **Régua Operacional (RAG):**
   * 🔴 **Falha:** Condição crítica/inaceitável que quebra o fluxo ou degrada a operação.
   * 🟡 **Regular:** Funciona com ressalvas; exige ajuste de parâmetro ou atenção.
   * 🟢 **Sucesso:** Comportamento ideal esperado em produção (meta do KR).

---

## Coleta de Dados (3 APIs + GTFS)

### OKR da Etapa
* **Objetivo (O):** Garantir a ingestão contínua de telemetria, clima e tráfego municipal com alto frescor, integridade e mínima dependência de dados simulados.
* **Resultados-Chave (KRs):**
  * **KR 1.1:** Atingir $\ge 99\%$ de taxa de sucesso (HTTP 200) nas chamadas às APIs externas a cada ciclo de 5 min.
  * **KR 1.2:** Manter a latência das chamadas HTTP em $\le 5\text{ segundos}$.
  * **KR 1.3:** Manter a idade média da telemetria do GPS (*Data Lag*) em $\le 120\text{ segundos}$ (2 min).
  * **KR 1.4:** Limitar o uso de dados em fallback (mock) a menos de $1\%$ dos ciclos diários.
  * **KR 1.5:** Garantir $100\%$ de integridade relacional nos arquivos GTFS estáticos.

### Tabela Operacional de Coleta
| O que medimos | Por que medimos | Como medir | 🔴 Falha | 🟡 Regular | 🟢 Sucesso (Meta KR) |
| :--- | :--- | :--- | :---: | :---: | :---: |
| **Taxa de Sucesso das APIs (ISR)** | Se a API externa falhar, todo o pipeline posterior fica cego. | % de chamadas HTTP com status `200` no ciclo de 5 min. | $< 95\%$ | $95\% \text{ a } 98,9\%$ | $\ge 99\%$ (KR 1.1) |
| **Latência das Chamadas** | APIs lentas atrasam ou estouram o tempo limite do Lambda. | Duração (em segundos) das requisições HTTP às APIs. | $> 15\text{ s}$ | $6\text{ a } 15\text{ s}$ | $\le 5\text{ s}$ (KR 1.2) |
| **Idade do Dado GPS (*Data Lag*)** | Ônibus com telemetria velha geram diagnósticos falsos de atraso. | $\text{Timestamp Atual} - \text{Timestamp do GPS } (ta)$. | $> 300\text{ s}$ (5 min) | $120\text{ a } 300\text{ s}$ | $\le 120\text{ s}$ (KR 1.3) |
| **Taxa de Fallback (HERE / Clima)** | Mede se estamos usando dados simulados/mock por falha de chave ou timeout. | (Chamadas em fallback ÷ Total de chamadas) × 100. | $> 5\%$ dos ciclos | $1\% \text{ a } 5\%$ | $< 1\%$ (KR 1.4) |
| **Integridade dos Arquivos GTFS** | GTFS corrompido quebra o cruzamento de linhas e trajetos. | Verificação de arquivos essenciais (`routes`, `trips`, `shapes`, `stop_times`). | Arquivo ausente/vazio | Linhas órfãs $> 5\%$ | $100\%$ íntegro (KR 1.5) |

---

## ETL & Cálculos Matemáticos

### OKR da Etapa
* **Objetivo (O):** Processar a malha de transporte em lote com rapidez computacional, gerando sub-índices matemáticos coerentes com a física das ruas e sem distorções estatísticas.
* **Resultados-Chave (KRs):**
  * **KR 2.1:** Executar o processamento completo do Lambda ETL em $\le 45\text{ segundos}$ por ciclo.
  * **KR 2.2:** Obter taxa de vínculo espacial (`cKDTree`) $\ge 95\%$ entre ônibus e trechos de tráfego da HERE.
  * **KR 2.3:** Manter a distribuição do $GO$ equilibrada no horário de pico (sem concentrar $\ge 85\%$ em uma única categoria).
  * **KR 2.4:** Garantir $0\%$ de registros com valores nulos ou inválidos (NaNs) no dataset persistido.
  * **KR 2.5:** Atingir índice de severidade climática $IAC \ge 55$ durante eventos confirmados de chuva severa ($> 10\text{ mm/h}$).

### Tabela Operacional do ETL
| O que medimos | Por que medimos | Como medir | 🔴 Falha | 🟡 Regular | 🟢 Sucesso (Meta KR) |
| :--- | :--- | :--- | :---: | :---: | :---: |
| **Tempo de Execução do ETL** | O ETL roda a cada 5 min; se demorar, a fila encavala. | Duração de execução do Lambda ETL (CloudWatch). | $> 120\text{ s}$ | $45\text{ a } 120\text{ s}$ | $\le 45\text{ s}$ (KR 2.1) |
| **Taxa de Vínculo Espacial (cKDTree)** | Garante que os ônibus encontrem trechos viários no raio de 1 km. | % de ônibus que localizaram $\ge 1$ trecho no raio. | $< 85\%$ | $85\% \text{ a } 94,9\%$ | $\ge 95\%$ (KR 2.2) |
| **Distribuição do Gargalo ($GO$)** | O score não pode polarizar tudo em normal (como na versão antiga). | % de linhas em cada nível de risco no horário de pico. | $\ge 95\%$ em uma categoria | Estabilizado $> 85\%$ | Equilibrada (~65% Est., ~25% Risco, ~10% Alto Risco) (KR 2.3) |
| **Valores Nulos ou Inválidos (NaNs)** | Erros matemáticos poluem o dataset que treina o ML. | Quantidade de campos nulos em colunas calculadas. | $> 0,5\%$ | Até $0,5\%$ tratados | $0\%$ nulos (KR 2.4) |
| **Sensibilidade do Clima ($IAC$)** | O índice climático deve reagir proporcionalmente a temporais. | Valor do $IAC$ em momentos de chuva confirmada ($> 10\text{ mm/h}$). | $IAC < 30$ (cego à chuva) | $30 \le IAC \le 55$ | $IAC \ge 55$ (KR 2.5) |

---

## Machine Learning (Foco Principal da Validação)

### OKR da Etapa
* **Objetivo (O):** Antecipar gargalos e sugerir o dimensionamento correto de veículos extras com antecedência hábil para despacho pelo CCO, minimizando alarmes falsos e surpresas.
* **Resultados-Chave (KRs):**
  * **KR 3.1:** Atingir Assertividade Temporal (*Hit Rate*) $\ge 75\%$ na previsão de **40 minutos** ($H_{40}$) e $\ge 85\%$ em **10 minutos** ($H_{10}$).
  * **KR 3.2:** Limitar a taxa de linhas em crise não previstas (*Linhas Surpresa / Falsos Negativos*) a $\le 20\%$.
  * **KR 3.3:** Alcançar sobreposição da malha em crise (*IoU / Jaccard*) $\ge 60\%$ entre o conjunto previsto e o realizado.
  * **KR 3.4:** Obter erro médio absoluto de dimensionamento de frota (*MAE do Déficit*) $\le 0,7$ veículos extras.
  * **KR 3.5:** Manter a estabilidade dos alertas (*Anti-Flicker*), com $\le 5\%$ de linhas alternando status em janelas de 15 minutos.

### 3.1 Entendimento do Lead Time de Antecipação
* **Horizonte de 10 minutos ($H_{10}$):** Alta acurácia matemática, porém tempo curto para deslocamento de frota da garagem.
* **Horizonte de 40 minutos ($H_{40}$):** Tempo ideal para acionamento do pátio e posicionamento do veículo reserva antes da superlotação.

### Tabela Operacional do Machine Learning
| O que medimos | Por que medimos | Como medir | 🔴 Falha | 🟡 Regular | 🟢 Sucesso (Meta KR) |
| :--- | :--- | :--- | :---: | :---: | :---: |
| **Assertividade Temporal (*Hit Rate*)** | Das linhas que o modelo disse que teriam gargalo em $t+\Delta t$, quantas realmente tiveram? | Cruzamento no banco após passar o tempo:<br>$\frac{\text{Linhas Confirmadas com Gargalo}}{\text{Linhas Previstas com Gargalo}} \times 100$ | $< 60\%$ (muito alarme falso) | $60\% \text{ a } 74,9\%$ | $\ge 75\%$ em $H_{40}$<br>$\ge 85\%$ em $H_{10}$ (KR 3.1) |
| **Taxa de Linhas Surpresa (*Omissão*)** | Linhas que colapsaram sem aviso prévio do modelo (Falsos Negativos). | $\frac{\text{Linhas em Gargalo NÃO Previstas}}{\text{Total de Linhas em Gargalo Real}} \times 100$ | $> 35\%$ das crises | $20\% \text{ a } 35\%$ | $\le 20\%$ (KR 3.2) |
| **Sobreposição da Malha (*IoU / Jaccard*)** | Mede a precisão de conjunto: acertou as mesmas linhas ou errou o alvo? | $\frac{\|\text{Linhas Previstas} \cap \text{Linhas Reais}\|}{\|\text{Linhas Previstas} \cup \text{Linhas Reais}\|} \times 100$ | $< 40\%$ | $40\% \text{ a } 59,9\%$ | $\ge 60\%$ (KR 3.3) |
| **Erro do Déficit de Ônibus (MAE)** | Se previu 1 ônibus e precisava de 4 (ou 0), a recomendação erra o dimensionamento. | Média do erro absoluto: $\text{Média}(\|\text{Déficit Previsto} - \text{Déficit Real}\|)$. | $> 1,5\text{ ônibus}$ | $0,8\text{ a } 1,5\text{ ônibus}$ | $\le 0,7\text{ ônibus}$ (KR 3.4) |
| **Estabilidade do Alerta (*Anti-Flicker*)** | Evita que uma linha fique alternando entre normal e crítico a cada 5 min, gerando confusão. | % de linhas que mudam de status mais de 2 vezes em menos de 15 minutos. | $> 15\%$ | $5\% \text{ a } 15\%$ | $\le 5\%$ (KR 3.5) |

---

## Front-End & Alertas (Grafana, RDS e SNS)

### OKR da Etapa
* **Objetivo (O):** Proporcionar visualização de baixa latência para a torre de controle e notificar o operador sobre riscos iminentes sem gerar sobrecarga ou fadiga de alertas.
* **Resultados-Chave (KRs):**
  * **KR 4.1:** Manter a latência de execução das queries analíticas no RDS em $\le 0,5\text{ segundo}$.
  * **KR 4.2:** Garantir tempo total de renderização dos dashboards no Grafana em $\le 2,0\text{ segundos}$.
  * **KR 4.3:** Entregar notificações críticas via AWS SNS em $\le 15\text{ segundos}$ após a inferência.
  * **KR 4.4:** Eliminar disparos repetidos aplicando regra de silenciamento (*cooldown*) de $\ge 20\text{ minutos}$ por linha.

### Tabela Operacional de Front-End & Alertas
| O que medimos | Por que medimos | Como medir | 🔴 Falha | 🟡 Regular | 🟢 Sucesso (Meta KR) |
| :--- | :--- | :--- | :---: | :---: | :---: |
| **Latência de Consulta no RDS** | O painel do Grafana não pode travar nem demorar para carregar. | Tempo de resposta das queries SQL principais. | $> 2,0\text{ s}$ | $0,5\text{ a } 2,0\text{ s}$ | $\le 0,5\text{ s}$ (KR 4.1) |
| **Tempo de Atualização no Grafana** | O operador precisa ver a situação atualizada sem delay perceptível. | Tempo para renderizar o dashboard completo. | $> 5,0\text{ s}$ | $2,0\text{ a } 5,0\text{ s}$ | $\le 2,0\text{ s}$ (KR 4.2) |
| **Latência de Envio de Alerta (SNS)** | Tempo entre a detecção do risco e o recebimento da notificação no CCO. | $\text{Timestamp Envio SNS} - \text{Timestamp Detecção}$. | $> 60\text{ s}$ | $15\text{ a } 60\text{ s}$ | $\le 15\text{ s}$ (KR 4.3) |
| **Controle de Fadiga (*Anti-Spam*)** | Bombardeio de e-mails da mesma linha faz o operador ignorar avisos. | Intervalo mínimo entre disparos para uma mesma linha em estado crítico contínuo. | Notifica a cada ciclo ($5\text{ min}$) | Notifica a cada $10\text{ a } 15\text{ min}$ | Notifica a cada $\ge 20\text{ min}$ *(com cooldown)* (KR 4.4) |

---

## Pipeline como um Todo (Visão Fim-a-Fim)

### OKR da Etapa
* **Objetivo (O):** Sustentar um pipeline distribuído em nuvem com alta disponibilidade, integridade de dados rigorosa e tempo de resposta ponta a ponta previsível.
* **Resultados-Chave (KRs):**
  * **KR 5.1:** Garantir latência fim-a-fim (*E2E Latency*) $\le 4\text{ minutos}$ do sinal de GPS na rua até a tela do CCO.
  * **KR 5.2:** Atingir $\ge 99\%$ de execuções completas com sucesso dos 288 ciclos diários do EventBridge.
  * **KR 5.3:** Manter $100\%$ de consistência e sincronia entre os registros persistidos no S3 e os gravados no RDS.

### Tabela Operacional do Pipeline
| O que medimos | Por que medimos | Como medir | 🔴 Falha | 🟡 Regular | 🟢 Sucesso (Meta KR) |
| :--- | :--- | :--- | :---: | :---: | :---: |
| **Latência Fim-a-Fim (*E2E Latency*)** | Tempo total desde o sinal do ônibus na rua até estar disponível no painel. | $\text{Hora da exibição no Grafana} - \text{Hora do GPS } (ta)$. | $> 10\text{ min}$ | $5\text{ a } 10\text{ min}$ | $\le 4\text{ min}$ (KR 5.1) |
| **Taxa de Execução do Pipeline** | Proporção de ciclos diários do EventBridge que completaram com sucesso. | $\frac{\text{Ciclos com Sucesso}}{\text{Total de Ciclos Programados (288)}} \times 100$ | $< 95\%$ | $95\% \text{ a } 98,9\%$ | $\ge 99\%$ (KR 5.2) |
| **Consistência de Carga (S3 vs. RDS)** | Garante que o total de linhas no CSV do S3 bate com o gravado no RDS. | $\text{Qtd Linhas no RDS} - \text{Qtd Linhas no CSV}$. | Diferença $> 0$ (perda de dados) | Atraso transitório de 1 ciclo | $100\%$ sincronizado (KR 5.3) |