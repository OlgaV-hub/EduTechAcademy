import boto3
import os
from dotenv import load_dotenv  # ← добавили

# загружаем переменные из .env
load_dotenv()

session = boto3.session.Session(
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    region_name=os.getenv("AWS_REGION")
)

s3 = session.client("s3")
bucket = os.getenv("S3_BUCKET")

print("AWS_REGION:", os.getenv("AWS_REGION"))
print("S3_BUCKET:", bucket)
print("AWS_ACCESS_KEY_ID:", os.getenv("AWS_ACCESS_KEY_ID"))
print("AWS_SECRET_ACCESS_KEY:", os.getenv("AWS_SECRET_ACCESS_KEY"))

try:
    response = s3.list_objects_v2(Bucket=bucket)
    print("OK! Conexión exitosa a S3.")
    print("Objetos en el bucket:", response.get("Contents", []))
except Exception as e:
    print("ERROR:", e)