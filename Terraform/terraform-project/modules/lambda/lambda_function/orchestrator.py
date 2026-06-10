import json
import boto3
import os
from datetime import datetime

lambda_client = boto3.client('lambda')
sns = boto3.client('sns')

def lambda_handler(event, context):
    """
    Lambda Orchestrator: Coordinates the data pipeline execution
    Runs on a schedule (EventBridge rule) to trigger Ingestion and ETL functions
    """
    try:
        ingestion_arn = os.environ['INGESTION_FUNCTION_ARN']
        etl_arn = os.environ['ETL_FUNCTION_ARN']
        topic_arn = os.environ['SNS_TOPIC_ARN']
        
        results = {
            'orchestration_id': f"orch-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            'timestamp': datetime.now().isoformat(),
            'steps': []
        }
        
        # Step 1: Invoke Ingestion Lambda
        try:
            print("Step 1: Invoking Lambda Ingestion...")
            response_ingestion = lambda_client.invoke(
                FunctionName=ingestion_arn,
                InvocationType='RequestResponse',
                Payload=json.dumps({})
            )
            results['steps'].append({
                'function': 'Ingestion',
                'status': 'success',
                'response': json.loads(response_ingestion['Payload'].read())
            })
        except Exception as e:
            results['steps'].append({
                'function': 'Ingestion',
                'status': 'error',
                'error': str(e)
            })
        
        # Step 2: Invoke ETL Lambda
        try:
            print("Step 2: Invoking Lambda ETL...")
            response_etl = lambda_client.invoke(
                FunctionName=etl_arn,
                InvocationType='RequestResponse',
                Payload=json.dumps({})
            )
            results['steps'].append({
                'function': 'ETL',
                'status': 'success',
                'response': json.loads(response_etl['Payload'].read())
            })
        except Exception as e:
            results['steps'].append({
                'function': 'ETL',
                'status': 'error',
                'error': str(e)
            })
        
        # Publish summary to SNS
        summary_message = f"""
Pipeline Orchestration Summary
================================
Orchestration ID: {results['orchestration_id']}
Timestamp: {results['timestamp']}

Steps Executed:
"""
        for step in results['steps']:
            summary_message += f"\n- {step['function']}: {step['status']}"
        
        sns.publish(
            TopicArn=topic_arn,
            Subject='Pipeline Orchestration - Summary',
            Message=summary_message
        )
        
        return {
            'statusCode': 200,
            'body': json.dumps(results)
        }
    except Exception as e:
        print(f"Error: {str(e)}")
        
        # Publish error message to SNS
        try:
            sns.publish(
                TopicArn=os.environ['SNS_TOPIC_ARN'],
                Subject='Pipeline Orchestration - Error',
                Message=f'Error during orchestration: {str(e)}'
            )
        except:
            pass
        
        return {
            'statusCode': 500,
            'body': json.dumps(f'Error: {str(e)}')
        }
