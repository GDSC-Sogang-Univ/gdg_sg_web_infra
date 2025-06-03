import json
import os

from .client import fetch_database_pages, page_to_markdown, update_post_status
from .s3_uploader import save_markdown_to_s3, upload_assets_to_s3
from .utils import get_secret

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

    if not auth_token or auth_token != FIXED_TOKEN:
        return {
            "statusCode": 403,
            "body": json.dumps({"message": "Unauthorized"}),
        }

    # 특정 ID만 업로드하는 경우
    target_custom_id = None
    body = event.get("body", None)
    if body:
        try:
            body_data = json.loads(body)
            target_custom_id = (
                body_data.get("data", {})
                .get("properties", {})
                .get("ID", {})
                .get("unique_id", {})
                .get("number", None)
            )
            if target_custom_id is not None:
                target_custom_id = str(target_custom_id)
        except json.JSONDecodeError:
            return {
                "statusCode": 400,
                "body": json.dumps({"message": "Invalid JSON format in body"}),
            }

    pages = fetch_database_pages(DATABASE_ID)
    matched = False

    for page in pages:
        page_title = "Untitled"
        category = "web"
        custom_id = None

        try:
            for key, value in page.get("properties", {}).items():
                if value.get("type") == "title":
                    page_title = "".join(
                        t.get("plain_text", "") for t in value.get("title", [])
                    )
                elif value.get("type") == "select":
                    category = value.get("select", {}).get("name", "web")
                elif key == "ID" and value.get("type") == "unique_id":
                    uid = value.get("unique_id", {})
                    custom_id = str(uid.get("number", ""))
        except Exception as e:
            print(f"Error parsing properties: {e}")
            continue

        if target_custom_id:
            if custom_id != target_custom_id:
                continue
            matched = True  # ID 일치 → 처리

        # Markdown 콘텐츠 생성 및 업로드
        page_markdown = page_to_markdown(page, page_title, custom_id)
        save_markdown_to_s3(page_markdown, category, custom_id, S3_BUCKET_NAME)
        upload_assets_to_s3(custom_id, category, S3_BUCKET_NAME)
        update_post_status(page["id"], "Uploaded")

        if target_custom_id:
            break  # 타겟 포스트만 처리했으면 루프 종료

    if target_custom_id and not matched:
        return {
            "statusCode": 404,
            "body": json.dumps(
                {"message": f"No post found with custom ID: {target_custom_id}"}
            ),
        }

    return {
        "statusCode": 200,
        "body": json.dumps({"message": "Upload Successful"}),
    }


if __name__ == "__main__":
    lambda_handler(None, None)
