import json
import os
import re
from datetime import datetime

import boto3
import urllib3

http = urllib3.PoolManager()


def get_secret(secret_name):
    """AWS Secrets Manager에서 비밀을 가져오기"""
    client = boto3.client("secretsmanager")
    try:
        response = client.get_secret_value(SecretId=secret_name)
        secret = response.get("SecretString", None)
        if secret:
            return json.loads(secret)
    except Exception as e:
        print(f"Error fetching secret {secret_name}: {e}")
        return None


def sanitize_filename(filename):
    """파일 이름에서 특수 문자를 제거"""
    return re.sub(r"[^\w\-_\.]", "_", filename)


def download_image(image_url, page_dir):
    """임시 Notion Image URL을 통해 다운로드"""
    original_name = image_url.split("/")[-1].split("?")[0]
    sanitized_name = sanitize_filename(original_name)

    # 임시 /tmp/assets/{page_dir} 경로 생성
    # 현재 assets 파일은 이미지뿐이므로 해당 함수에서 생성
    tmp_dir = f"/tmp/assets/{page_dir}"
    os.makedirs(tmp_dir, exist_ok=True)

    # 이미지 저장 경로
    local_path = os.path.join(tmp_dir, sanitized_name)

    try:
        # 이미지 다운로드
        response = http.request("GET", image_url, preload_content=False)

        if response.status >= 200 and response.status < 300:
            # 파일 저장
            with open(local_path, "wb") as file:
                for chunk in response.stream(1024):  # 1KB씩 스트리밍
                    file.write(chunk)
            print(f"Image saved locally: {local_path}")
        else:
            print(
                f"Failed to download image: {image_url}, HTTP status: {response.status}"
            )
            return None
    except Exception as e:
        print(f"Error downloading image {image_url}: {e}")
        return None
    finally:
        response.release_conn()  # 연결 해제

    return local_path


def format_date(iso_date):
    """ISO 8601 날짜를 YYYY/MM/DD 형식으로 변환"""
    try:
        dt = datetime.fromisoformat(iso_date.replace("Z", "+00:00"))  # UTC 시간대 처리
        return dt.strftime("%Y/%m/%d")
    except Exception as e:
        print(f"Error formatting date: {e}")
        return iso_date  # 변환 실패 시 원본 반환


def generate_metadata(page, page_title):
    """Notion 페이지 데이터를 기반으로 MDX 메타데이터 생성"""
    try:
        created_time = page.get("created_time", "")
        date = format_date(created_time)
        description = (
            page.get("properties", {})
            .get("description", {})
            .get("rich_text", [{}])[0]
            .get("plain_text", "")
        )
        tags = [
            t.get("name", "")
            for t in page.get("properties", {}).get("tags", {}).get("multi_select", [])
        ]
        author = (
            page.get("properties", {})
            .get("author", {})
            .get("people", [{}])[0]
            .get("name", "Anonymous")
        )

        # MDX 메타데이터 구성
        metadata = f"""---
title: {page_title}
date: {date}
description: {description}
tags: {tags}
author: {author}
---
"""
        return metadata
    except Exception as e:
        print(f"Error generating metadata for page {page['id']}: {e}")
        return ""
