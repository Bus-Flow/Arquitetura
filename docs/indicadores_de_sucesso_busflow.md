# Indicadores de Sucesso (KPIs) — Projeto BusFlow

**Documento Prático para Validação com a Equipe**  
**Projeto:** BusFlow — Inteligência Operacional de Transporte Público  
**Objetivo:** Definir o que medir em cada etapa, a justificativa e os intervalos objetivos de **Falha**, **Regular** e **Sucesso**.

---

## Como ler este documento
Cada etapa possui uma tabela padronizada com:
* **O que medimos:** A métrica exata.
* **Por que medimos:** A razão prática/operacional.
* **Como medir:** A origem do dado ou cálculo simples.
* **Régua de Avaliação:**
  * 🔴 **Falha:** O sistema está com problema grave ou dado inutilizável.
  * 🟡 **Regular:** Funciona, mas exige ajuste, calibração ou atenção.
  * 🟢 **Sucesso:** Comportamento ideal esperado em produção.

---

## 1. Coleta de Dados (3 APIs + GTFS)

Garante que os dados de entrada (SPTrans Olho Vivo, OpenWeather, HERE Traffic e GTFS) cheguem íntegros, rápidos e sem dados velhos.

| O que medimos | Por que medimos | Como medir | 🔴 Falha | 🟡 Regular | 🟢 Sucesso |
| :--- | :--- | :--- | :---: | :---: | :---: |
| **Taxa de Sucesso das APIs (ISR)** | Se a API externa falhar, todo o pipeline posterior fica cego. | % de chamadas HTTP com status `200` no ciclo de 5 min. | $< 95\%$ | $95\% \text{ a } 98,9\%$ | $\ge 99\%$ |
| **Latência das Chamadas** | APIs lentas atrasam ou estouram o tempo limite do Lambda. | Duração (em segundos) das requisições HTTP às APIs. | $> 15\text{ s}$ | $6\text{ a } 15\text{ s}$ | $\le 5\text{ s}$ |
| **Idade do Dado GPS (*Data Lag*)** | Ônibus com telemetria velha geram diagnósticos falsos de atraso. | $\text{Timestamp Atual} - \text{Timestamp do GPS } (ta)$. | $> 300\text{ s}$ (5 min) | $120\text{ a } 300\text{ s}$ | $\le 120\text{ s}$ (2 min) |
| **Taxa de Fallback (HERE / Clima)** | Mede se estamos usando dados simulados/mock por falha de chave ou timeout. | (Chamadas que caíram em fallback ÷ Total de chamadas) × 100. | $> 5\%$ dos ciclos | $1\% \text{ a } 5\%$ | $< 1\%$ (dados reais) |
| **Integridade dos Arquivos GTFS** | GTFS corrompido quebra o cruzamento de linhas e trajetos. | Verificação de arquivos essenciais (`routes`, `trips`, `shapes`, `stop_times`). | Arquivo ausente ou vazio | Linhas órfãs $> 5\%$ | $100\%$ íntegro |

---

## 2. ETL & Cálculos Matemáticos

Mede se os algoritmos espaciais (`cKDTree`, `IDW`) e as fórmulas dos sub-índices ($IAC$, $GT$, $HP$, $AC$, $DFI$, $GO$) fazem sentido na prática e não saturam.

| O que medimos | Por que medimos | Como medir | 🔴 Falha | 🟡 Regular | 🟢 Sucesso |
| :--- | :--- | :--- | :---: | :---: | :---: |
| **Tempo de Execução do ETL** | O ETL roda a cada 5 min; se demorar muito, a fila de processamento encavala. | Tempo total de execução do Lambda ETL (CloudWatch). | $> 120\text{ s}$ | $45\text{ a } 120\text{ s}$ | $\le 45\text{ s}$ |
| **Taxa de Vínculo Espacial (cKDTree)** | Garante que os ônibus encontrem trechos viários da HERE no raio de 1 km. | % de ônibus que localizaram ao menos 1 trecho no raio. | $< 85\%$ | $85\% \text{ a } 94,9\%$ | $\ge 95\%$ |
| **Distribuição do Gargalo ($GO$)** | O score não pode concentrar tudo em uma categoria só (como ocorria na versão antiga). | % de linhas classificadas em cada nível de risco no horário de pico. | $\ge 95\%$ em uma única categoria | Estabilizado $> 85\%$ | Distribuição equilibrada<br>*(~65% Est., ~25% Risco, ~10% Alto Risco)* |
| **Valores Nulos ou Inválidos (NaNs)** | Erros matemáticos (divisão por zero) poluem o dataset que vai para o ML. | Quantidade de campos nulos em colunas calculadas no arquivo CSV. | $> 0,5\%$ dos registros | Até $0,5\%$ tratados com default | $0\%$ registros nulos |
| **Sensibilidade do Clima ($IAC$)** | O índice climático deve subir quando chover de verdade. | Valor do $IAC$ em momentos de chuva confirmada ($> 10\text{ mm/h}$). | $IAC < 30$ (cego à chuva) | $30 \le IAC \le 55$ | $IAC \ge 55$ (reagiu ao clima) |

---

## 3. Machine Learning

Avalia se as previsões do modelo têm **precisão real**, se o **tempo de antecedência** é útil para o operador e se o que foi previsto de fato se confirmou após o tempo decorrido.

### 3.1 Horizonte de Previsão vs. Tempo Útil de Reação (Lead Time)
* **Horizonte de 10 minutos:** Excelente precisão matemática, porém **tempo curto** para deslocar ônibus da garagem.
* **Horizonte de 40 minutos:** **Tempo ideal para o CCO** acionar o pátio e posicionar carros reserva, porém com maior desafio de acurácia.

### 3.2 Tabela de Métricas do ML

| O que medimos | Por que medimos | Como medir | 🔴 Falha | 🟡 Regular | 🟢 Sucesso |
| :--- | :--- | :--- | :---: | :---: | :---: |
| **Assertividade Temporal (*Hit Rate*)** | Das linhas que o modelo disse que teriam gargalo em $t+\Delta t$, quantas realmente tiveram? | Cruzamento no banco após passar o tempo:<br>$\frac{\text{Linhas Confirmadas com Gargalo}}{\text{Linhas Previstas com Gargalo}} \times 100$ | $< 60\%$ (muito alarme falso) | $60\% \text{ a } 74,9\%$ | $\ge 75\%$ em $H_{40}$<br>$\ge 85\%$ em $H_{10}$ |
| **Taxa de Linhas Surpresa (*Omissão*)** | Linhas que entraram em colapso sem que o modelo tenha previsto nada (Falsos Negativos). | $\frac{\text{Linhas em Gargalo NÃO Previstas}}{\text{Total de Linhas em Gargalo Real}} \times 100$ | $> 35\%$ das linhas em crise | $20\% \text{ a } 35\%$ | $\le 20\%$ |
| **Sobreposição da Malha (*IoU / Jaccard*)** | Mede a precisão do conjunto: acertou as mesmas linhas ou errou o alvo? | $\frac{\|\text{Linhas Previstas} \cap \text{Linhas Reais}\|}{\|\text{Linhas Previstas} \cup \text{Linhas Reais}\|} \times 100$ | $< 40\%$ | $40\% \text{ a } 59,9\%$ | $\ge 60\%$ |
| **Erro do Déficit de Ônibus (MAE)** | Se previu déficit de 1 ônibus e precisava de 4 (ou 0), a recomendação erra o dimensionamento. | Média do erro absoluto: $\text{Média}(\|\text{Déficit Previsto} - \text{Déficit Real}\|)$. | $> 1,5\text{ ônibus}$ | $0,8\text{ a } 1,5\text{ ônibus}$ | $\le 0,7\text{ ônibus}$ |
| **Estabilidade do Alerta (*Anti-Flicker*)** | Evita que uma linha fique alternando entre normal e crítico a cada 5 min, enlouquecendo o CCO. | % de linhas que mudam de status mais de 2 vezes em menos de 15 minutos. | $> 15\%$ | $5\% \text{ a } 15\%$ | $\le 5\%$ (status consistente) |

---

## 4. Front-End & Alertas (Grafana, RDS e SNS)

Garante que o operador do CCO receba a informação sem lentidão na tela e sem sofrer com bombardeio de e-mails repetidos (*fadiga de alertas*).

| O que medimos | Por que medimos | Como medir | 🔴 Falha | 🟡 Regular | 🟢 Sucesso |
| :--- | :--- | :--- | :---: | :---: | :---: |
| **Latência de Consulta no RDS** | O painel do Grafana não pode travar nem demorar para carregar as listas. | Tempo de execução das queries SQL principais que alimentam o Grafana. | $> 2,0\text{ s}$ | $0,5\text{ a } 2,0\text{ s}$ | $\le 0,5\text{ s}$ |
| **Tempo de Atualização no Grafana** | O operador precisa ver a situação atualizada sem delay perceptível. | Tempo total para renderizar o dashboard completo na tela do operador. | $> 5,0\text{ s}$ | $2,0\text{ a } 5,0\text{ s}$ | $\le 2,0\text{ s}$ |
| **Latência de Envio de Alerta (SNS)** | Do momento em que o risco é detectado até o e-mail/notificação chegar ao CCO. | Timestamp de envio do SNS menos o timestamp de detecção no processamento. | $> 60\text{ s}$ | $15\text{ a } 60\text{ s}$ | $\le 15\text{ s}$ |
| **Controle de Fadiga (*Anti-Spam*)** | Enviar alertas repetidos a cada 5 min para a mesma linha faz o operador ignorar os avisos. | Intervalo mínimo entre disparos para uma mesma linha mantida em estado crítico. | Notifica a cada ciclo ($5\text{ min}$) | Notifica a cada $10\text{ a } 15\text{ min}$ | Notifica a cada $\ge 20\text{ min}$ *(com cooldown)* |

---

## 5. Pipeline como um Todo (Visão Fim-a-Fim)

Métricas gerais do sistema para comprovar estabilidade, velocidade e confiabilidade da arquitetura.

| O que medimos | Por que medimos | Como medir | 🔴 Falha | 🟡 Regular | 🟢 Sucesso |
| :--- | :--- | :--- | :---: | :---: | :---: |
| **Latência Fim-a-Fim (*E2E Latency*)** | Quanto tempo leva desde o sinal de GPS do ônibus na rua até o dado estar disponível no painel. | $\text{Hora da exibição no Grafana} - \text{Hora do envio do GPS pelo ônibus } (ta)$. | $> 10\text{ min}$ | $5\text{ a } 10\text{ min}$ | $\le 4\text{ min}$ |
| **Taxa de Execução do Pipeline** | Proporção de ciclos do EventBridge que completaram com sucesso sem interrupção. | $\frac{\text{Ciclos Concluídos com Sucesso no Dia}}{\text{Total de Ciclos Programados no Dia (288)}} \times 100$ | $< 95\%$ | $95\% \text{ a } 98,9\%$ | $\ge 99\%$ |
| **Consistência de Carga (S3 vs. RDS)** | Garante que o total de linhas geradas no CSV do S3 bate exatamente com o gravado no RDS. | $\text{Qtd Linhas no RDS} - \text{Qtd Linhas no CSV}$. | Diferença $> 0$ (perda de dados) | Atraso transitório de 1 ciclo | $100\%$ sincronizado |

---

## Roteiro de 5 Minutos para Validação

1. **Sobre a Coleta:** Concordam que toleramos no máximo 2 minutos de atraso no GPS do ônibus?
2. **Sobre o ETL:** A nova regra de distribuição do $GO$ (evitando saturar 99% em normal) está clara para todos?
3. **Sobre o ML (Ponto Crítico):**
   * Faz sentido mantermos a meta de **75% de acerto para a previsão de 40 minutos** e **85% para a de 10 minutos**?
   * O critério de **Hit Rate** (validar 10 ou 40 min depois se as linhas previstas realmente estavam com problema) responde à nossa dúvida principal de precisão?
4. **Sobre Alertas:** Concordam em limitar o disparo do SNS a no máximo 1 alerta a cada 20 minutos para a mesma linha (evitando spam de e-mails)?
