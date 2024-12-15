import os

from client import fetch_database_pages, page_to_markdown
from s3_uploader import save_markdown_to_s3, upload_assets_to_s3

# 환경 변수에서 설정 가져오기
DATABASE_ID = os.getenv("DATABASE_ID", "your-database-id")
S3_BUCKET_NAME = os.getenv("POST_BUCKET", "your-s3-bucket-name")

assert DATABASE_ID != "your-database-id", "DATABASE_ID 환경 변수를 설정하세요"
assert S3_BUCKET_NAME != "your-s3-bucket-name", "S3_BUCKET_NAME 환경 변수를 설정하세요"


def lambda_handler(event, context):
    """Lambda 엔트리 포인트"""

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
        except Exception as e:
            print(f"Error fetching title: {e}")

        # Markdown 콘텐츠 생성
        page_markdown = page_to_markdown(page, page_title)

        # Markdown 콘텐츠를 S3에 저장
        save_markdown_to_s3(page_markdown, page_title, S3_BUCKET_NAME)

        # 필요한 assets를 S3에 업로드
        upload_assets_to_s3(page_title, S3_BUCKET_NAME)


if __name__ == "__main__":
    lambda_handler(None, None)
