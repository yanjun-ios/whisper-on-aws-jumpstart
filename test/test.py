import boto3
from urllib import parse

# Configure AWS credentials
session = boto3.Session()
s3 = session.client('s3')

# Set the bucket name and file path
bucket_name = 'whisper-bucket-091063646508'
file_path = '0002.mp4'

# Set the object key (file name in S3)
object_key = file_path

# Set the tags for the uploaded object
tags = {
    'model_size': 'large',
    'llm_handle': 'asr/tag/summary'
}

# Upload the file to S3 and add tags in a single call
try:
    s3.upload_file(
        file_path,
        bucket_name,
        object_key,
        ExtraArgs={
            'Tagging': parse.urlencode(tags)
        }
    )
    print(f"File '{file_path}' uploaded successfully to S3 bucket '{bucket_name}' with tags '{tags}'")
except Exception as e:
    print(f"Error uploading file and adding tags: {e}")
    exit(1)
