import json
import os

from client import fetch_database_pages, page_to_markdown, update_post_status
from s3_uploader import save_markdown_to_s3, upload_assets_to_s3
from utils import get_secret

# 환경 변수에서 설정 가져오기
DATABASE_ID = os.getenv("DATABASE_ID", "your-database-id")
S3_BUCKET_NAME = os.getenv("POST_BUCKET", "your-s3-bucket-name")

assert DATABASE_ID != "your-database-id", "DATABASE_ID 환경 변수를 설정하세요"
assert S3_BUCKET_NAME != "your-s3-bucket-name", "S3_BUCKET_NAME 환경 변수를 설정하세요"


secret = get_secret("notion-api-key")
FIXED_TOKEN = secret.get("auth-token", None)

assert FIXED_TOKEN, "auth token를 가져올 수 없습니다"


def lambda_handler(event, context):
    """Lambda 엔트리 포인트"""

    headers = event.get("headers", {})
    auth_token = headers.get("Authorization", None)

    # 인증 토큰 검증
    if not auth_token or auth_token != FIXED_TOKEN:
        return {
            "statusCode": 403,
            "body": json.dumps({"message": "Unauthorized"}),
        }

    # 특정 포스트만 업로드하는 경우
    target_post = None
    body = event.get("body", None)
    if body:
        try:
            body_data = json.loads(body)
            target_post = body_data.get("Name", None)
        except json.JSONDecodeError:
            return {
                "statusCode": 400,
                "body": json.dumps({"message": "Invalid JSON format in body"}),
            }

    # 노션 데이터베이스로부터 페이지 fetch
    pages = fetch_database_pages(DATABASE_ID)
    for page in pages:

        page_title = "Untitled"
        try:
            for key, value in page.get("properties", {}).items():
                if value.get("type") == "title":
                    page_title = "".join(
                        t.get("plain_text", "") for t in value.get("title", [])
                    )
                    break
            if target_post and target_post != page_title:
                continue
        except Exception as e:
            print(f"Error fetching title: {e}")

        # Markdown 콘텐츠 생성
        page_markdown = page_to_markdown(page, page_title)

        # Markdown 콘텐츠를 S3에 저장
        save_markdown_to_s3(page_markdown, page_title, S3_BUCKET_NAME)

        # 필요한 assets를 S3에 업로드
        upload_assets_to_s3(page_title, S3_BUCKET_NAME)

        update_post_status(page["id"], "Uploaded")

    return {
        "statusCode": 200,
        "body": json.dumps({"message": "Upload Successful"}),
    }


if __name__ == "__main__":
    lambda_handler(None, None)
