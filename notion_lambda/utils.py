import json
import os
import re

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


def extract_text_with_annotations(rich_text):
    """Notion rich_text 데이터를 Markdown 스타일로 변환"""
    if not rich_text or not isinstance(rich_text, list):
        return ""

    md_text = ""
    for text_obj in rich_text:
        text = text_obj.get("plain_text", "")
        annotations = text_obj.get("annotations", {})

        # Markdown 스타일 적용
        if annotations.get("bold"):
            text = f"**{text}**"
        if annotations.get("italic"):
            text = f"*{text}*"
        if annotations.get("strikethrough"):
            text = f"~~{text}~~"
        if annotations.get("underline"):
            text = f"<u>{text}</u>"  # Markdown에는 표준 밑줄이 없으므로 HTML 사용
        if annotations.get("code"):
            text = f"`{text}`"

        md_text += text

    return md_text or ""


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
