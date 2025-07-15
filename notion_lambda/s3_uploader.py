import os

import boto3
from botocore.exceptions import ClientError

s3_client = boto3.client("s3")


def save_markdown_to_s3(content, category, page_id, bucket_name):
    """Markdown 콘텐츠를 S3에 저장"""
    s3_key = f"posts/{category}/{page_id}/page.mdx"
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


def upload_assets_to_s3(page_id, category, bucket_name):
    """필요한 assets을 S3에 업로드"""
    s3_key = f"posts/{category}/{page_id}"
    assets_local_path = f"/tmp/assets/{page_id}"

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


def delete_post_from_s3(custom_id, category, bucket_name):
    """S3에서 특정 포스트의 모든 파일을 삭제"""
    try:
        # 삭제할 포스트의 키
        target_key = f"posts/{category}/{custom_id}/"
        try:
            # assets 폴더의 모든 객체 리스트
            response = s3_client.list_objects_v2(Bucket=bucket_name, Prefix=target_key)

            if "Contents" in response:
                # 모든 객체 삭제
                objects_to_delete = [
                    {"Key": obj["Key"]} for obj in response["Contents"]
                ]
                if objects_to_delete:
                    s3_client.delete_objects(
                        Bucket=bucket_name, Delete={"Objects": objects_to_delete}
                    )
                    print(
                        f"Deleted {len(objects_to_delete)} asset files from {target_key}"
                    )
                else:
                    print(f"No asset files found in {target_key}")
            else:
                print(f"No assets folder found: {target_key}")

        except Exception as e:
            print(f"Error deleting assets from {target_key}: {e}")

        return True

    except Exception as e:
        print(f"Error in delete_post_from_s3: {e}")
        return False
