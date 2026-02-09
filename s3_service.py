import boto3
from botocore.exceptions import ClientError
from config import get_settings
from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from io import BytesIO
import uuid
from datetime import datetime, timedelta

settings = get_settings()

class S3Service:
    def __init__(self):
        self.s3_client = boto3.client(
            's3',
            region_name=settings.AWS_REGION,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
        )
        self.bucket = settings.AWS_S3_BUCKET
    
    def add_watermark_to_pdf(self, pdf_bytes: bytes, user_id: int) -> bytes:
        """Add watermark to PDF"""
        try:
            pdf_reader = PdfReader(BytesIO(pdf_bytes))
            pdf_writer = PdfWriter()
            
            watermark_text = f"NotesHub - User ID: {user_id}"
            
            for page in pdf_reader.pages:
                packet = BytesIO()
                can = canvas.Canvas(packet, pagesize=letter)
                can.setFont("Helvetica", 8)
                can.setFillColorRGB(0.7, 0.7, 0.7, alpha=0.3)
                can.drawString(50, 30, watermark_text)
                can.save()
                
                packet.seek(0)
                watermark_pdf = PdfReader(packet)
                page.merge_page(watermark_pdf.pages[0])
                pdf_writer.add_page(page)
            
            output = BytesIO()
            pdf_writer.write(output)
            output.seek(0)
            return output.read()
        except Exception as e:
            print(f"Watermark error: {e}")
            return pdf_bytes
    
    def upload_note(self, file_content: bytes, filename: str, user_id: int) -> str:
        """Upload PDF note with watermark to S3"""
        watermarked_content = self.add_watermark_to_pdf(file_content, user_id)
        
        file_key = f"notes-pdf/{user_id}/{uuid.uuid4()}_{filename}"
        
        try:
            self.s3_client.put_object(
                Bucket=self.bucket,
                Key=file_key,
                Body=watermarked_content,
                ContentType='application/pdf'
            )
            return file_key
        except ClientError as e:
            raise Exception(f"S3 upload failed: {str(e)}")
    
    def upload_book_image(self, file_content: bytes, filename: str, user_id: int) -> str:
        """Upload book image to S3"""
        file_key = f"book-images/{user_id}/{uuid.uuid4()}_{filename}"
        
        try:
            self.s3_client.put_object(
                Bucket=self.bucket,
                Key=file_key,
                Body=file_content,
                ContentType='image/jpeg'
            )
            return file_key
        except ClientError as e:
            raise Exception(f"S3 upload failed: {str(e)}")
    
    def generate_presigned_url(self, file_key: str, expiration: int = 3600) -> str:
        """Generate presigned URL for private file access"""
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket, 'Key': file_key},
                ExpiresIn=expiration
            )
            return url
        except ClientError as e:
            raise Exception(f"Failed to generate URL: {str(e)}")
    
    def delete_file(self, file_key: str):
        """Delete file from S3"""
        try:
            self.s3_client.delete_object(Bucket=self.bucket, Key=file_key)
        except ClientError as e:
            print(f"S3 delete failed: {str(e)}")

s3_service = S3Service()
