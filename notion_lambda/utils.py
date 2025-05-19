import json
import mimetypes
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


def download_thumbnail(page, page_dir):
    """페이지 커버를 썸네일로 다운로드"""
    try:
        cover = page.get("cover")
        if not cover:
            print("No cover found.")
            return None

        cover_type = cover.get("type")
        image_url = ""

        if cover_type == "external":
            image_url = cover.get("external", {}).get("url", "")
        elif cover_type == "file":
            image_url = cover.get("file", {}).get("url", "")

        if not image_url:
            print("Cover URL not found.")
            return None

        local_path = download_image(image_url, page_dir)
        if not local_path:
            print("Image download failed.")
            return None

        _, ext = os.path.splitext(local_path)

        # 확장자 확인 후 thumbnail 파일명 지정
        thumbnail_path = os.path.join(os.path.dirname(local_path), f"thumbnail{ext}")
        os.rename(local_path, thumbnail_path)
        print(f"Thumbnail saved: {thumbnail_path}")
        return thumbnail_path

    except Exception as e:
        print(f"Error fetching thumbnail image: {e}")
        return None


def generate_metadata(page, page_title):
    """Notion 페이지 데이터를 기반으로 MDX 메타데이터 생성"""
    try:
        created_time = page.get("created_time", "")
        date = format_date(created_time)

        # description (rich_text)
        desc_rich = (
            page.get("properties", {}).get("description", {}).get("rich_text", [])
        )
        description = desc_rich[0].get("plain_text", "") if desc_rich else ""

        # tags (multi_select)
        tags_raw = page.get("properties", {}).get("tags", {}).get("multi_select", [])
        tags = [t.get("name", "") for t in tags_raw if "name" in t]

        # author (people)
        author_raw = page.get("properties", {}).get("author", {}).get("people", [])
        author = author_raw[0].get("name", "Anonymous") if author_raw else "Anonymous"

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
        print(f"Error generating metadata for page {page.get('id', 'UNKNOWN')}: {e}")
        return ""
