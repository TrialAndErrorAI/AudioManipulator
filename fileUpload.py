import boto3
from dataplane import s3_upload
from botocore.client import Config

INDEX_FILES_BUCKET = 'vox-ai-model-index-files'
PTH_FILES_BUCKET = 'vox-ai-model-pth-files'
CONTENT_FILES_BUCKET = 'vox-ai'

CONTENT_FILES_BUCKET_URL = 'https://r2.voxapp.ai'

# define enum for bucket types
class BucketType:
  INDEX_FILES = 1
  PTH_FILES = 2
  CONTENT_FILES = 3

S3Connect = boto3.client('s3', 
             endpoint_url='https://40ad419de279f41e9626e2faf500b6b4.r2.cloudflarestorage.com',
             aws_access_key_id='7da645d13a990ecc11f684221ed975e3',
             aws_secret_access_key='2ed0fe3463962449e5dbc8a66fb1f5ff49e06ecb2badac62120cc2c8caadc3e0',
             config=Config(signature_version='s3v4'),
             region_name='us-east-1')
            
def upload_file(file_path, filename, bucketType: BucketType):
  print(f"Uploading file {filename}...")
  if bucketType == BucketType.INDEX_FILES:
    bucket = INDEX_FILES_BUCKET
  elif bucketType == BucketType.PTH_FILES:
    bucket = PTH_FILES_BUCKET
  elif bucketType == BucketType.CONTENT_FILES:
    bucket = CONTENT_FILES_BUCKET
  else:
    raise ValueError("Invalid bucket type")

  rs = s3_upload(Bucket=bucket, 
            S3Client=S3Connect,
            SourceFilePath=file_path,
            TargetFilePath=filename,
            UploadMethod="File"
          )
  if rs['result'] == 'OK':
      if bucketType == BucketType.CONTENT_FILES:
        return f"{CONTENT_FILES_BUCKET_URL}/{filename}"
      else:
        return rs['Path']
  else:
    raise Exception(f"Failed to upload file {filename}, Response: {rs}")
  