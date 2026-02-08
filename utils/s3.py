import boto3
from config.settings import AWS_REGION, AWS_ACCESS_KEY, AWS_SECRET_KEY, AWS_BUCKET

s3_client = boto3.client('s3', region_name=AWS_REGION, aws_access_key_id=AWS_ACCESS_KEY, aws_secret_access_key=AWS_SECRET_KEY)

def upload_to_s3(file_content, file_key):
    s3_client.put_object(Bucket=AWS_BUCKET, Key=file_key, Body=file_content, ContentType='application/pdf', ACL='public-read')
    return f"https://{AWS_BUCKET}.s3.{AWS_REGION}.amazonaws.com/{file_key}"
