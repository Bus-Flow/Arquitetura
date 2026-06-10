import boto3
import pandas as pd
import os
import io

s3 = boto3.client('s3')
sns = boto3.client('sns')

TOPICO_SNS_ARN = os.environ.get('SNS_TOPIC_ARN','')

colunas_tratadas = {
    "Card ID": "card_id",
    "Título": "titulo",
    "Criado em": "criado_em",
    "Fase": "fase",
    "Anexos": "anexos",
    "Ações que foram tomadas após escalar o problema": "acoes_pos_escalonamento",
    "Ações que foram tomadas durante atendimento n1": "acoes_durante_atendimento",
    "Data de finalização do chamado": "data_finalizacao",
    "Descrição Chamado": "descricao_chamado",
    "O atendente pode resolver este problema?": "resolvido_por_atendente",
    "categoria": "categoria",
    "cnpj_empresa": "cnpj_empresa",
    "data_solicitacao": "data_solicitacao",
    "email_solicitante": "email_solicitante",
    "nome_fantasia_empresa": "nome_fantasia_empresa",
    "nome_solicitante": "nome_solicitante",
    "Responsável Chamado": "responsavel_chamado",
    "Especialista responsável": "especialista_responsavel",
}

def lambda_handler(event, context):
    bucket_origem = event['Records'][0]['s3']['bucket']['name']
    chave_arquivo = event['Records'][0]['s3']['object']['key']
    bucket_destino = 'trusted-busflow-2025-2'

    try:
        response = s3.get_object(Bucket=bucket_origem, Key=chave_arquivo)
        df_raw = pd.read_csv(response['Body'], encoding='utf-8')
        df_raw = df_raw.loc[:, ~df_raw.columns.duplicated()]
        df_tratado = df_raw.rename(columns=colunas_tratadas)

        if 'criado_em' in df_tratado.columns:
            df_tratado['criado_em'] = pd.to_datetime(df_tratado['criado_em'], errors='coerce')
            df_tratado['criado_em'] = df_tratado['criado_em'].dt.strftime('%d/%m/%Y %H:%M').fillna('')

        buffer = io.BytesIO()
        df_tratado.to_csv(buffer, index=False, sep=';', encoding='utf-8-sig')
        buffer.seek(0)

        nome_arquivo_tratado = os.path.basename(chave_arquivo).replace('raw-', 'trusted-')

        s3.put_object(
            Bucket=bucket_destino,
            Key=nome_arquivo_tratado,
            Body=buffer.read()
        )

        mensagem = f"""
📂 Relatório tratado com sucesso!

Olá,

Seu arquivo foi processado e salvo com sucesso no bucket *trusted-busflow*.

🔗 Local do arquivo: s3://{bucket_destino}/{nome_arquivo_tratado}

Atenciosamente,  
Equipe busflow 🚀
"""

        # ✅ Publica no tópico SNS diretamente
        sns.publish(
            TopicArn=TOPICO_SNS_ARN,
            Message=mensagem.strip(),
            Subject='[busflow] Relatório tratado com sucesso'
        )

        return {
            'statusCode': 200,
            'body': 'Relatório tratado e notificação enviada com sucesso.'
        }

    except Exception as e:
        erro_msg = f"[ERRO] Falha ao processar o arquivo: {str(e)}"
        print(erro_msg)
        return {
            'statusCode': 500,
            'body': erro_msg
        }
      

