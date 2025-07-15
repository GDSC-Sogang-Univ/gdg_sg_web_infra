import json
import os

from client import fetch_database_pages, page_to_markdown, update_post_status
from s3_uploader import delete_post_from_s3, save_markdown_to_s3, upload_assets_to_s3
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
    headers = event.get("headers", {})
    auth_token = headers.get("Authorization", None)

    if not auth_token or auth_token != FIXED_TOKEN:
        return {
            "statusCode": 403,
            "body": json.dumps({"message": "Unauthorized"}),
        }

    # 경로에 따라 업로드/삭제 분기
    path = event.get("resource") or event.get("path", "")
    # API Gateway Proxy 통합이면 resource, 아니면 path 사용
    if path.endswith("/upload"):
        return handle_upload_request(event)
    elif path.endswith("/delete"):
        return handle_delete_request(event)
    else:
        return {
            "statusCode": 404,
            "body": json.dumps({"message": "Invalid endpoint"}),
        }


def find_page_by_custom_id(database_id, custom_id):
    """custom_id로 Notion page 객체 찾기"""
    pages = fetch_database_pages(database_id)
    for page in pages:
        try:
            for key, value in page.get("properties", {}).items():
                if key == "ID" and value.get("type") == "unique_id":
                    uid = value.get("unique_id", {})
                    if str(uid.get("number", "")) == str(custom_id):
                        return page
        except Exception:
            continue
    return None


def handle_delete_request(event):
    body = event.get("body", None)
    if not body:
        return {
            "statusCode": 400,
            "body": json.dumps(
                {"message": "Request body is required for delete operation"}
            ),
        }
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

    if not target_custom_id:
        return {
            "statusCode": 400,
            "body": json.dumps({"message": "custom_id is required in request body"}),
        }
    # Notion page 객체 찾기
    page = find_page_by_custom_id(DATABASE_ID, target_custom_id)
    if not page:
        return {
            "statusCode": 404,
            "body": json.dumps(
                {"message": f"No post found with custom ID: {target_custom_id}"}
            ),
        }
    category = "web"
    try:
        for key, value in page.get("properties", {}).items():
            if value.get("type") == "select":
                category = value.get("select", {}).get("name", "web")
    except Exception as e:
        print(f"Error parsing category: {e}")
    # S3에서 파일 삭제
    success = delete_post_from_s3(target_custom_id, category, S3_BUCKET_NAME)
    if success:
        update_post_status(page["id"], "Not Uploaded")
        return {
            "statusCode": 200,
            "body": json.dumps(
                {"message": f"Post {target_custom_id} deleted successfully"}
            ),
        }
    else:
        return {
            "statusCode": 500,
            "body": json.dumps(
                {"message": f"Failed to delete post {target_custom_id}"}
            ),
        }


def handle_upload_request(event):
    # custom_id는 필수
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

    if not target_custom_id:
        return {
            "statusCode": 400,
            "body": json.dumps({"message": "custom_id is required in request body"}),
        }

    page = find_page_by_custom_id(DATABASE_ID, target_custom_id)
    if not page:
        return {
            "statusCode": 404,
            "body": json.dumps(
                {"message": f"No post found with custom ID: {target_custom_id}"}
            ),
        }

    page_title = "Untitled"
    category = "web"
    custom_id = target_custom_id
    try:
        for key, value in page.get("properties", {}).items():
            if value.get("type") == "title":
                page_title = "".join(
                    t.get("plain_text", "") for t in value.get("title", [])
                )
            elif value.get("type") == "select":
                category = value.get("select", {}).get("name", "web")
    except Exception as e:
        print(f"Error parsing properties: {e}")

    page_markdown = page_to_markdown(page, page_title, category, custom_id)
    delete_post_from_s3(custom_id, category, S3_BUCKET_NAME)
    save_markdown_to_s3(page_markdown, category, custom_id, S3_BUCKET_NAME)
    upload_assets_to_s3(custom_id, category, S3_BUCKET_NAME)
    update_post_status(page["id"], "Uploaded")

    return {
        "statusCode": 200,
        "body": json.dumps({"message": "Upload Successful"}),
    }


if __name__ == "__main__":
    lambda_handler(None, None)
