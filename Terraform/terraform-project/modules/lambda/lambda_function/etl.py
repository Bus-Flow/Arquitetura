import json
import boto3
import pandas as pd
import os
from datetime import datetime
import io

s3 = boto3.client('s3')
sns = boto3.client('sns')

def lambda_handler(event, context):
    """
    Lambda ETL: Processes data from Raw bucket and stores in Trusted bucket
    Triggered by S3 events when CSV files are uploaded to Raw bucket
    """
    try:
        bucket_raw = os.environ['BUCKET_RAW']
        bucket_trusted = os.environ['BUCKET_TRUSTED']
        topic_arn = os.environ['SNS_TOPIC_ARN']
        
        # Get the S3 object from the event
        if 'Records' in event:
            # Triggered by S3 event
            key = event['Records'][0]['s3']['object']['key']
            bucket = event['Records'][0]['s3']['bucket']['name']
        else:
            # Manual invocation for testing
            key = 'ingestion/raw_data.csv'
            bucket = bucket_raw
        
        # Download file from S3
        obj = s3.get_object(Bucket=bucket, Key=key)
        df = pd.read_csv(io.BytesIO(obj['Body'].read()))
        
        # Data transformation/cleaning
        df['processed_at'] = datetime.now().isoformat()
        df = df.dropna()
        df = df.drop_duplicates()
        
        # Save processed data to Trusted bucket
        trusted_key = key.replace('ingestion/', 'trusted/').replace('.csv', f'_processed_{datetime.now().strftime("%Y%m%d%H%M%S")}.csv')
        
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False)
        
        s3.put_object(
            Bucket=bucket_trusted,
            Key=trusted_key,
            Body=csv_buffer.getvalue()
        )
        
        # Publish success message to SNS
        sns.publish(
            TopicArn=topic_arn,
            Subject='Lambda ETL - Success',
            Message=f'ETL process completed successfully.\nProcessed {len(df)} rows.\nOutput: s3://{bucket_trusted}/{trusted_key}'
        )
        
        return {
            'statusCode': 200,
            'body': json.dumps(f'ETL completed successfully. Processed {len(df)} rows.')
        }
    except Exception as e:
        print(f"Error: {str(e)}")
        
        # Publish error message to SNS
        try:
            sns.publish(
                TopicArn=os.environ['SNS_TOPIC_ARN'],
                Subject='Lambda ETL - Error',
                Message=f'Error during ETL: {str(e)}'
            )
        except:
            pass
        
        return {
            'statusCode': 500,
            'body': json.dumps(f'Error: {str(e)}')
        }
