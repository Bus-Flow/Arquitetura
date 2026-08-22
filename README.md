# 🚌 BusFlow - Arquitetura de Dados & Inteligência Operacional

[![Terraform](https://img.shields.io/badge/IaC-Terraform-623CE4.svg?logo=terraform&logoColor=white)](https://www.terraform.io/)
[![AWS](https://img.shields.io/badge/Cloud-AWS%20Serverless-FF9900.svg?logo=amazon-aws&logoColor=white)](https://aws.amazon.com/)
[![Python](https://img.shields.io/badge/Python-3.9-3776AB.svg?logo=python&logoColor=white)](https://www.python.org/)
[![PostgreSQL](https://img.shields.io/badge/Database-PostgreSQL%20RDS-336791.svg?logo=postgresql&logoColor=white)](https://www.postgresql.org/)

O **BusFlow** é uma solução de engenharia de dados e inteligência operacional orientada a eventos para o monitoramento, identificação de gargalos e previsão de déficit de frotas de transporte público urbano na cidade de São Paulo.


## Documentações do Projeto
* [Especificação do Pipeline e Tabela TRUSTED](docs/pipeline_dados_arquitetura_v3.md)
* [Guia de Segurança, Variáveis e Gatilhos](docs/seguranca_gatilhos_e_variaveis.md)
* [Análise e Exemplo Prático da Tabela TRUSTED](docs/exemplo_dataset_trusted_analise.md)
* [Plano de Reorganização e Registro de Mudanças](docs/plano_reorganizacao_repositorio.md)

---

## Estrutura Padronizada do Repositório

```text
BusFlow/
├── docs/                              # Documentações técnicas e acadêmicas
│   ├── pipeline_dados_arquitetura_v3.md   # Especificação da arquitetura e camadas RAW/TRUSTED
│   ├── seguranca_gatilhos_e_variaveis.md  # Variáveis centralizadas, segurança e EventBridge
│   ├── exemplo_dataset_trusted_analise.md # Análise matemática e auditoria da camada TRUSTED
│   ├── plano_reorganizacao_repositorio.md # Registro detalhado da reorganização do repositório
│   ├── diagramas/                     # Diagramas visuais organizados
│   │   ├── bpmn/                      # Processos As-Is e To-Be (.bpmn, .svg, .png)
│   │   └── arquitetura/               # Diagramas de arquitetura (.drawio, .svg, .xml)
│   └── tcc/                           # Monografia e relatórios (BusFlow.docx, BusFlow.pdf)
│
├── data/                              # Amostras e dados locais controlados
│   ├── raw/                           # Payloads brutos JSON e ZIPs GTFS
│   │   └── gtfs/                      # Arquivos GTFS SPTrans
│   └── samples/                       # Datasets tratados (fato_operacao_exemplo.csv)
│
├── src/                               # Código-fonte Python da aplicação
│   ├── lambdas/                       # Funções Lambda Serverless da AWS
│   │   ├── ingestion_realtime.py      # Ingestão tempo real (SPTrans + OpenWeather)
│   │   ├── ingestion_gtfs.py          # Ingestão inteligente do GTFS
│   │   └── etl.py                     # Motor ETL de cálculo de índices operacionais
│   └── collectors_local/              # Scripts auxiliares para execução local
│       ├── coletor_tempo_real.py      # Coletor local Olho Vivo + Clima
│       └── coletor_gtfs.py            # Coletor local GTFS
│
├── terraform/                         # Infraestrutura como Código (IaC)
│   ├── main.tf                        # Módulo raiz da arquitetura AWS
│   ├── variables.tf                   # Declaração centralizada de variáveis
│   ├── outputs.tf                     # Outputs de recursos provisionados
│   ├── terraform.tfvars.example       # Template seguro para credenciais
│   └── modules/                       # Módulos: ec2, lambda, network, rds, s3, sagemaker, sns
│
├── .env.example                       # Template de variáveis de ambiente locais
├── .gitignore                         # Regras rigorosas de proteção de segredos
└── README.md                          # Portal central de documentação e onboarding
```

---

## Como Executar e Implantar

### 1. Configurar Variáveis de Ambiente
Copie o template de variáveis do Terraform e configure suas credenciais:
```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
```
Edite o arquivo `terraform.tfvars` preenchendo as chaves da SPTrans, OpenWeather e lista de e-mails do SNS.

### 2. Implantar Infraestrutura na AWS
```bash
cd terraform
terraform init
terraform apply -auto-approve
```

### 3. Teste Manual dos Gatilhos (Sob Demanda)

* **Executar Ingestão GTFS:**
  ```bash
  aws lambda invoke --function-name <lambda_ingestion_gtfs_arn> --payload '{}' response.json
  ```
* **Executar Ingestão Tempo Real (Dispara o ETL automaticamente no S3):**
  ```bash
  aws lambda invoke --function-name <lambda_ingestion_arn> --payload '{}' response.json
  ```
* **Verificar Logs do ETL:**
  ```bash
  aws logs tail /aws/lambda/<lambda_etl_arn> --since 5m
  ```