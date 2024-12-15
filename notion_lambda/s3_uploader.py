import os

import boto3
from botocore.exceptions import ClientError

s3_client = boto3.client("s3")


def save_markdown_to_s3(content, page_title, bucket_name):
    """Markdown 콘텐츠를 S3에 저장"""
    s3_key = f"pages/{page_title}/page.mdx"
    markdown_local_path = "/tmp/page.md"

    # Markdown 파일을 /tmp에 저장
    with open(markdown_local_path, "w", encoding="utf-8") as f:
        f.write(content)

    try:
        # S3에 업로드
        s3_client.upload_file(markdown_local_path, bucket_name, s3_key)
        s3_url = f"https://{bucket_name}.s3.amazonaws.com/{s3_key}"
        print(f"Uploaded to S3: {s3_url}")
        return s3_url
    except ClientError as e:
        print(f"Error uploading to S3: {e}")
        return None


def upload_assets_to_s3(page_title, bucket_name):
    """필요한 assets을 S3에 업로드"""
    s3_key = f"pages/{page_title}"
    assets_local_path = f"/tmp/assets/{page_title}"

    try:
        # assets 파일들 하나씩 S3에 업로드
        for root, _, files in os.walk(assets_local_path):
            for file in files:
                local_file = os.path.join(root, file)
                s3_file = os.path.relpath(local_file, assets_local_path)
                s3_client.upload_file(local_file, bucket_name, f"{s3_key}/{s3_file}")
                print(f"Uploaded to S3: {s3_key}/{s3_file}")
    except ClientError as e:
        print(f"Error uploading assets to S3: {e}")
