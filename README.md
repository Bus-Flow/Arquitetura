# 🚌 BusFlow - Arquitetura de Dados & Inteligência Operacional

[![Terraform](https://img.shields.io/badge/IaC-Terraform-623CE4.svg?logo=terraform&logoColor=white)](https://www.terraform.io/)
[![AWS](https://img.shields.io/badge/Cloud-AWS%20Serverless-FF9900.svg?logo=amazon-aws&logoColor=white)](https://aws.amazon.com/)
[![Python](https://img.shields.io/badge/Python-3.9-3776AB.svg?logo=python&logoColor=white)](https://www.python.org/)
[![PostgreSQL](https://img.shields.io/badge/Database-PostgreSQL%20RDS-336791.svg?logo=postgresql&logoColor=white)](https://www.postgresql.org/)

O **BusFlow** é uma solução de engenharia de dados e inteligência operacional orientada a eventos para o monitoramento, identificação de gargalos e previsão de déficit de frotas de transporte público urbano na cidade de São Paulo.


## 📚 Documentações do Projeto & Governança

A pasta [`docs/`](docs/) foi estruturada em módulos temáticos para facilitar a consulta acadêmica e operacional:

* **01. Arquitetura:**
  * [Especificação do Pipeline e Camadas RAW/TRUSTED](docs/01_arquitetura/pipeline_dados_arquitetura_v3.md)
  * [Guia de Segurança, Variáveis e Gatilhos EventBridge](docs/01_arquitetura/seguranca_gatilhos_e_variaveis.md)
* **02. Governança, SLA e Métricas:**
  * [Plano de Auditoria, SLAs e Métricas de Sucesso (OKRs)](docs/02_governanca_sla_e_metricas/plano_auditoria_sla_e_metricas_sucesso.md)
* **03. Engenharia de Dados & Banco:**
  * [Fluxo de Dados e Inteligência Espacial da API HERE](docs/03_engenharia_de_dados_e_banco/especificacao_fluxo_calculos_here_trafego.md)
  * [Relatório de Validação do Dataset TRUSTED com HERE](docs/03_engenharia_de_dados_e_banco/relatorio_validacao_dataset_trusted_here.md)
  * [Script DDL Oficial do RDS PostgreSQL](src/database/schema_busflow_rds.sql)
* **04. Artigo Acadêmico & TCC:**
  * [📄 Relatório Fonte da Verdade para Atualização do Artigo](docs/04_artigo_academico_tcc/relatorio_atualizacao_artigo.md)
* **Diagramas Visuais:**
  * [Desenho da Arquitetura AWS v3.1 (.drawio)](docs/diagramas/arquitetura/arquiteturaV3.drawio)
  * [Diagrama Entidade-Relacionamento Transparente (.png)](docs/diagramas/modelagem_dados_busflow.png)

---

## Estrutura Padronizada do Repositório

```text
BusFlow/
├── docs/                                  # Central de documentações técnicas e acadêmicas
│   ├── 01_arquitetura/                    # Pipelines e especificações de infraestrutura
│   ├── 02_governanca_sla_e_metricas/      # Auditoria operacional, SLAs e OKRs
│   ├── 03_engenharia_de_dados_e_banco/    # Algoritmos espaciais HERE e modelagem analítica
│   ├── 04_artigo_academico_tcc/           # Relatório consolidado (fonte da verdade para o artigo)
│   └── diagramas/                         # Diagramas visuais (arquitetura, DER e BPMN)
│       ├── arquitetura/                   # Diagramas AWS (.drawio, .png)
│       ├── bpmn/                          # Processos operacionais As-Is e To-Be
│       ├── modelagem_dados_busflow.png    # DER com fundo transparente em alta resolução
│       └── modelagem_dados_busflow_transparente.svg
│
├── data/                                  # Amostras de dados controlados
│   ├── raw/gtfs/                          # Arquivos estáticos do GTFS SPTrans
│   └── samples/                           # Amostras tratadas
│
├── machine learning/                      # Modelos preditivos (Random Forest) e notebooks
│   ├── RF-Trusted-cod.ipynb               # Notebook de experimentação e validação
│   ├── Analise_Resultados_RF_BusFlow.pdf  # Avaliação de métricas (Hit Rate e MAE)
│   └── busflow_dados_ficticios/           # Gerador de massa de teste
│
├── src/                                   # Código-fonte da aplicação
│   ├── database/                          # Scripts e DDLs do banco de dados
│   │   └── schema_busflow_rds.sql         # DDL completo do RDS (tabelas, índices e views de auditoria)
│   ├── lambdas/                           # Funções Serverless AWS
│   │   ├── ingestion_realtime.py          # Ingestão Olho Vivo + OpenWeather + HERE -> S3 RAW
│   │   ├── ingestion_gtfs.py              # Ingestão de tabelas estáticas GTFS -> S3 RAW
│   │   └── etl.py                         # Motor ETL com cKDTree espacial -> S3 TRUSTED + RDS PostgreSQL
│   └── collectors_local/                  # Scripts de coleta para teste local
│
├── terraform/                             # Infraestrutura como Código (IaC)
│   ├── main.tf                            # Módulo raiz integrado (VPC, RDS, EC2, Lambdas, S3)
│   ├── variables.tf                       # Parâmetros configuráveis
│   ├── outputs.tf                         # Endpoints e IDs gerados
│   ├── terraform.tfvars.example           # Template seguro de credenciais
│   └── modules/                           # Módulos: ec2, lambda, network, rds, s3, sagemaker, sns
│
├── scripts/                               # Scripts operacionais e de migração
│   └── setup_database.py                  # Inicializador controlado e rastreável do banco RDS
│
├── .gitignore                             # Regras rigorosas de proteção de segredos
└── README.md                              # Portal central de documentação e onboarding
```

---

## Guia Rápido Pós-Pull para a Equipe

Se você acabou de sincronizar a sua máquina via `git pull origin main`, siga este passo a passo para colocar o ambiente em conformidade:

### 1. Atualizar e Provisionar a Infraestrutura AWS (Terraform)
Nesta versão, a instância EC2 dedicada para Machine Learning (`busflow-rf-ec2`) e as regras de Security Group integradas ao RDS PostgreSQL na porta 5432 foram adicionadas.

```bash
# 1. Navegue até o diretório do Terraform
cd terraform

# 2. Atualize os provedores (necessário para baixar as atualizações do lock)
terraform init -upgrade

# 3. Valide os arquivos de configuração
terraform validate

# 4. Aplique as modificações na AWS
terraform apply
```

> **Nota de Variáveis:** Verifique se o seu arquivo `terraform/terraform.tfvars` contém os valores preenchidos para as credenciais da SPTrans, OpenWeather, HERE e lista de e-mails para notificações no SNS.

### 2. Inicializar o Esquema do Banco RDS (Tabelas e Views de Auditoria)
Seguindo as **melhores práticas de mercado (desacoplamento entre IaC e DDLs de banco)**, o Terraform cria a infraestrutura com segurança (RDS PostgreSQL em sub-rede privada).

Para criar as tabelas operacionais, dimensões e as **views de auditoria contínua com total rastreabilidade**, execute o script Python disponibilizado:

```bash
# Executar a partir da raiz do projeto:
python scripts/setup_database.py \
    --host <rds_endpoint_gerado_no_terraform> \
    --password <sua_senha_do_rds>
```

> *Alternativamente, você também pode abrir o arquivo [`src/database/schema_busflow_rds.sql`](src/database/schema_busflow_rds.sql) diretamente no DBeaver, pgAdmin ou VS Code e executá-lo.*

> **O que esse script cria?**
> * **Dimensões:** `dim_linha`, `dim_linha_parada`
> * **Fatos Operacionais:** `fato_linha_operacao`, `fato_veiculo_posicao`, `fato_previsao_ml`, `fato_alerta`
> * **Auditoria & Governança:** Tabela `fato_auditoria_pipeline` e Views de Auditoria (`v_grafana_validacao_ml`, `v_auditoria_metricas_ml`, `v_auditoria_frescor_dados`).

### 3. Teste Manual dos Gatilhos do Pipeline

* **Executar Ingestão GTFS (Manual):**
  ```bash
  aws lambda invoke --function-name <lambda_ingestion_gtfs_name> --payload '{}' response.json
  ```
* **Executar Ingestão em Tempo Real:**
  *(A ingestão salva no bucket S3 RAW, que automaticamente dispara o Lambda ETL por evento S3)*:
  ```bash
  aws lambda invoke --function-name <lambda_ingestion_name> --payload '{}' response.json
  ```
* **Acompanhar Logs do ETL e Auditoria:**
  ```bash
  aws logs tail /aws/lambda/<lambda_etl_name> --since 5m --follow
  ```