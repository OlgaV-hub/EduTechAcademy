# services/s3.py
# import boto3
# import os
# from uuid import uuid4


# session = boto3.session.Session(
#     aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
#     aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
#     region_name=os.getenv("AWS_REGION"),
# )

# s3 = session.client("s3")
# BUCKET = os.getenv("S3_BUCKET")


# def subir_imagen_curso(file_storage, prefix="courses/"):

#     filename = file_storage.filename or "image"
#     ext = filename.rsplit(".", 1)[-1].lower()
#     if ext == "":
#         ext = "png"

#     key = f"{prefix}{uuid4()}.{ext}"

#     s3.upload_fileobj(
#         file_storage,
#         BUCKET,
#         key,
#         ExtraArgs={
#             "ACL": "public-read",                    
#             "ContentType": file_storage.mimetype or "image/png"
#         }
#     )

#     return key


# def url_publica(key):
#     """
#     Возвращает ПРЯМОЙ публичный URL.
#     Работает потому что ACL=public-read.
#     """
#     if not key:
#         return None

#     region = os.getenv("AWS_REGION")
#     bucket = BUCKET

#     return f"https://{bucket}.s3.{region}.amazonaws.com/{key}"

import os
from uuid import uuid4

import boto3


AWS_REGION = os.getenv("AWS_REGION") or "us-east-2"
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
S3_BUCKET = os.getenv("S3_BUCKET")


session = boto3.session.Session(
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION,
)

s3 = session.client("s3") if AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY else None


def subir_imagen_curso(file_storage, prefix="courses/"):
    """
    Загружает файл в S3 и возвращает key.
    Если файл не выбран или S3 не настроен — возвращает None.
    """


    if not file_storage or not file_storage.filename:
        return None


    if not (s3 and S3_BUCKET):
        print("[S3] Falta configuración (s3 o S3_BUCKET). No se sube imagen.")
        return None


    filename = file_storage.filename
    if "." in filename:
        ext = filename.rsplit(".", 1)[-1].lower()
    else:
        ext = "png"

    key = f"{prefix}{uuid4()}.{ext}"


    try:
        s3.upload_fileobj(
            file_storage,
            S3_BUCKET,
            key,
            ExtraArgs={
                "ACL": "public-read",
                "ContentType": file_storage.mimetype or "image/png",
            },
        )
        print(f"[S3] Imagen subida: bucket={S3_BUCKET}, key={key}")
    except Exception as e:

        print(f"[S3] Error al subir imagen: {e}")
        return None

    return key


def url_publica(key: str | None):
    """
    Собирает публичный URL по key.
    Работает, потому что объект сохранён с ACL=public-read.
    """
    if not key:
        return None

    region = AWS_REGION
    bucket = S3_BUCKET
    if not bucket:
        return None

    return f"https://{bucket}.s3.{region}.amazonaws.com/{key}"