import json

from notion_lambda.client import (
    fetch_database_pages,
    fetch_page_content,
    page_to_markdown,
)
from notion_lambda.converter import get_block_content

# aws cli 설치 후 테스트 가능 (notion api_key secret manager로 가져옴)
# pytest -s tests/unit/test_notion_parser.py -v

# 벡터 임베딩 페이지
valid_page_id = "59645fc6e41d48a3a4999d7b4cea76e0"

# def test_fetch_page_content():
#     result = fetch_page_content(valid_page_id)
#     assert result is not None
#     assert isinstance(result, dict)
#     assert "results" in result

#     print("\n=== Notion Page Content ===")
#     print(json.dumps(result, indent=2, ensure_ascii=False))
#     print("==========================\n")


def test_convert():
    result = fetch_page_content(valid_page_id)

    content = ""
    for block in result["results"]:
        content += get_block_content(block, "test") + "\n"

    print("\n=== Converted Content ===")
    print(content)
    print("==========================\n")
