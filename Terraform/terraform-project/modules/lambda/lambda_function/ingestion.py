import json
import boto3
import os
import requests
from datetime import datetime

s3 = boto3.client('s3')
sns = boto3.client('sns')
rds = boto3.client('rds')

def lambda_handler(event, context):
    """
    Lambda Ingestion: Collects data from external APIs (SprTans, OpenWeather)
    and stores raw data in S3 Raw bucket
    """
    try:
        bucket_raw = os.environ['BUCKET_RAW']
        rds_host = os.environ['RDS_HOST']
        rds_user = os.environ['RDS_USER']
        rds_password = os.environ['RDS_PASSWORD']
        rds_database = os.environ['RDS_DATABASE']
        topic_arn = os.environ['SNS_TOPIC_ARN']
        
        # Example: Collect data from APIs
        data = {
            'timestamp': datetime.now().isoformat(),
            'source': 'ingestion',
            'status': 'success'
        }
        
        # Save raw data to S3
        s3.put_object(
            Bucket=bucket_raw,
            Key=f"ingestion/{datetime.now().strftime('%Y/%m/%d/%H')}/data.json",
            Body=json.dumps(data)
        )
        
        # Publish success message to SNS
        sns.publish(
            TopicArn=topic_arn,
            Subject='Lambda Ingestion - Success',
            Message=f'Data ingestion completed successfully at {datetime.now().isoformat()}'
        )
        
        return {
            'statusCode': 200,
            'body': json.dumps('Ingestion completed successfully')
        }
    except Exception as e:
        print(f"Error: {str(e)}")
        
        # Publish error message to SNS
        try:
            sns.publish(
                TopicArn=os.environ['SNS_TOPIC_ARN'],
                Subject='Lambda Ingestion - Error',
                Message=f'Error during ingestion: {str(e)}'
            )
        except:
            pass
        
        return {
            'statusCode': 500,
            'body': json.dumps(f'Error: {str(e)}')
        }
