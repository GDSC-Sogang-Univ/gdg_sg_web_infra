import json
import os

import urllib3
from converter import get_block_content
from utils import download_thumbnail, generate_metadata, get_secret

# Notion API 설정
api_secret = get_secret("notion-api-key")
NOTION_API_KEY = api_secret.get("notion-api-key")
NOTION_API_URL = "https://api.notion.com/v1"
HEADERS = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28",
}

http = urllib3.PoolManager()


def make_request(method, url, headers=None, body=None):
    """Notion API 요청 처리"""
    try:
        response = http.request(
            method,
            url,
            headers=headers or {},
            body=json.dumps(body) if body else None,
        )
        if response.status >= 200 and response.status < 300:
            return json.loads(response.data.decode("utf-8"))
        elif response.status == 401:
            raise Exception("Invalid Notion API key")
        elif response.status == 404:
            raise Exception("Notion resource not found")
        elif response.status == 429:
            raise Exception("Notion API rate limit exceeded")
        else:
            print(f"Error: {response.status}, {response.data}")
            return None
    except Exception as e:
        print(f"Request error: {e}")
        return None


def fetch_database_pages(database_id):
    """데이터베이스 내 페이지 가져오기"""
    results = []
    next_cursor = None

    while True:
        url = f"{NOTION_API_URL}/databases/{database_id}/query"
        payload = {"start_cursor": next_cursor} if next_cursor else {}

        data = make_request("POST", url, headers=HEADERS, body=payload)
        if not data:
            break

        results.extend(data.get("results", []))
        next_cursor = data.get("next_cursor")
        if not next_cursor:
            break

    return results


def fetch_page_content(page_id):
    """페이지 콘텐츠 가져오기"""
    url = f"{NOTION_API_URL}/blocks/{page_id}/children"
    data = make_request("GET", url, headers=HEADERS)
    return data if data else {}


def page_to_markdown(page, page_title, page_id):
    """페이지 데이터를 MDX 형식으로 변환"""
    try:
        # 메타데이터 생성
        metadata = generate_metadata(page, page_title)

        # thumbnail 다운로드
        thumbnail_path = download_thumbnail(page, page_id)

        # 페이지 콘텐츠 변환
        page_content = fetch_page_content(page["id"])
        md_content = []

        for block in page_content.get("results", []):
            content = get_block_content(block, f"{page_id}")
            if content.strip():
                md_content.append(content)

        # 최종 콘텐츠 결합
        return metadata + "\n\n" + "\n\n".join(md_content)
    except Exception as e:
        print(f"Error processing page {page['id']}: {e}")
        return ""


def fetch_table_rows(block_id):
    """Notion API를 통해 테이블 행 데이터 가져오기"""
    url = f"https://api.notion.com/v1/blocks/{block_id}/children"
    response = make_request("GET", url, headers=HEADERS)  # Notion API 요청
    if response:
        return response.get("results", [])
    return []


def update_post_status(post_id, status):
    """Notion API를 통해 포스트 상태 업데이트"""
    url = f"{NOTION_API_URL}/pages/{post_id}"
    payload = {"properties": {"status": {"status": {"name": status}}}}
    try:
        result = make_request("PATCH", url, headers=HEADERS, body=payload)
        if result is not None:
            print("Post status updated successfully.")
        else:
            print("Error updating post status: No response or failed request.")
    except Exception as e:
        print(f"Exception occurred: {e}")
