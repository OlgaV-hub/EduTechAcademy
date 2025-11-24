# services/s3.py
import boto3
import os
from uuid import uuid4


session = boto3.session.Session(
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    region_name=os.getenv("AWS_REGION"),
)

s3 = session.client("s3")
BUCKET = os.getenv("S3_BUCKET")


def subir_imagen_curso(file_storage, prefix="courses/"):

    filename = file_storage.filename or "image"
    ext = filename.rsplit(".", 1)[-1].lower()
    if ext == "":
        ext = "png"

    key = f"{prefix}{uuid4()}.{ext}"

    s3.upload_fileobj(
        file_storage,
        BUCKET,
        key,
        ExtraArgs={
            "ACL": "public-read",                    
            "ContentType": file_storage.mimetype or "image/png"
        }
    )

    return key


def url_publica(key):
    """
    Возвращает ПРЯМОЙ публичный URL.
    Работает потому что ACL=public-read.
    """
    if not key:
        return None

    region = os.getenv("AWS_REGION")
    bucket = BUCKET

    return f"https://{bucket}.s3.{region}.amazonaws.com/{key}"