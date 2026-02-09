import boto3
import os

AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
AWS_BUCKET = os.getenv("AWS_S3_BUCKET", "noteshub-free-wala")

s3_client = boto3.client('s3', 
    region_name=AWS_REGION, 
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"), 
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY")
)

def upload_file_to_s3(file_content, file_key):
    s3_client.put_object(Bucket=AWS_BUCKET, Key=file_key, Body=file_content, ContentType='application/pdf', ACL='public-read')
    return f"https://{AWS_BUCKET}.s3.{AWS_REGION}.amazonaws.com/{file_key}"
