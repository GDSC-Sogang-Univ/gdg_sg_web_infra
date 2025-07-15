import os

from utils import download_image

list_counter = {"numbered": 0}


def reset_list_counter():
    """리스트 번호를 리셋"""
    global list_counter
    list_counter["numbered"] = 0


def get_number_format(number):
    """들여쓰기 레벨에 따른 번호 형식 반환

    Args:
        number: 현재 번호
        indent_level: 들여쓰기 레벨
    """

    return str(number)  # 1, 2, 3, ...


def extract_text_with_annotations(rich_text):
    """Notion rich_text 데이터를 Markdown 스타일로 변환"""
    if not rich_text or not isinstance(rich_text, list):
        return ""

    md_text = ""
    for text_obj in rich_text:
        text = text_obj.get("plain_text", "")
        annotations = text_obj.get("annotations", {})
        link = text_obj.get("text", {}).get("link", {})

        # Markdown 스타일 적용
        if annotations.get("bold"):
            text = f"**{text}**"
        if annotations.get("italic"):
            text = f"*{text}*"
        if annotations.get("strikethrough"):
            text = f"<s>{text}</s>"  # 취소선
        if annotations.get("underline"):
            text = f"<u>{text}</u>"  # Markdown에는 표준 밑줄이 없으므로 HTML 사용
        if annotations.get("code"):
            text = f"`{text}`"

        if link:
            url = link.get("url", "")
            if url:
                text = f"[{text}]({url})"

        md_text += text

    return md_text or ""


def handle_paragraph(block_data):
    """Markdown 변환: Paragraph"""
    return extract_text_with_annotations(block_data.get("rich_text", [])) or ""


def handle_heading(block_data, level):
    """Markdown 변환: Heading (H1, H2, H3)"""
    text = extract_text_with_annotations(block_data.get("rich_text", []))
    return f"{'#' * level} {text}" if text else f"{'#' * level} "


def handle_list_item(block_data, prefix_type, counter=None, indent_level=0):
    """
    Markdown 변환: List Item (Bulleted or Numbered)
    - prefix_type: "-" (bulleted), "numbered" (numbered list)
    - counter: numbered list를 위한 현재 번호
    - indent_level: 들여쓰기 레벨
    """
    text = extract_text_with_annotations(block_data.get("rich_text", []))

    if prefix_type == "-":
        return f"- {text}"
    elif prefix_type == "numbered":
        if counter is not None:
            number = get_number_format(counter)
            return f"{number}. {text}"
    return f"{prefix_type} {text}"  # 기본 fallback


def handle_quote(block_data):
    """Markdown 변환: Quote"""
    text = extract_text_with_annotations(block_data.get("rich_text", []))
    return f"> {text}" if text else "> "


def handle_code(block_data):
    """Markdown 변환: Code Block"""
    text = extract_text_with_annotations(block_data.get("rich_text", []))
    language = block_data.get("language", "plaintext")
    return f"```{language}\n{text}\n```" if text else f"```{language}\n\n```"


def handle_image(block_data, category, page_dir):
    """Markdown 변환: Image"""
    image_url = block_data.get("file", {}).get("url", "")
    caption = extract_text_with_annotations(block_data.get("caption", []))

    if image_url:
        # 이미지 다운로드
        local_image_path = download_image(image_url, page_dir)
        if local_image_path:
            # 같은 폴더 안에서 이미지 파일 이름만 사용
            image_filename = os.path.basename(local_image_path)
            return f"![{caption}](/posts/{category}/{page_dir}/{image_filename})"
        else:
            return f"![{caption}]({image_url})"
    return "![Image]"


def handle_callout(block_data):
    """Markdown 변환: Callout"""
    text = extract_text_with_annotations(block_data.get("rich_text", []))
    icon = block_data.get("icon", {}).get("emoji", "")  # 이모지 아이콘 추출
    return f"> {icon} {text}" if icon else f"> {text}"


def handle_to_do(block_data):
    """Markdown 변환: To Do"""
    text = extract_text_with_annotations(block_data.get("rich_text", []))
    checked = block_data.get("checked", False)
    checkbox = "[x]" if checked else "[ ]"
    return f"{checkbox} {text}"


def handle_toggle(block_data, page_dir):
    """Markdown 변환: Toggle TODO"""
    pass


def handle_table(block_data, block_id):
    """Markdown 변환: Table TODO"""
    pass


def handle_divider(block_data):
    """Markdown 변환: Divider"""
    return "---"


def handle_child_block(block_data, page_dir, category, indent_level=0):
    """자식 블록 처리

    Args:
        block_data: 부모 블록 데이터
        page_dir: 페이지 디렉토리
        indent_level: 현재 들여쓰기 레벨
    """
    from client import fetch_page_content

    child_blocks = fetch_page_content(block_data["id"])
    if not child_blocks or "results" not in child_blocks:
        return ""

    reset_list_counter()
    child_contents = []

    for child_block in child_blocks["results"]:
        child_content = get_block_content(
            child_block, page_dir, category, indent_level + 1
        )
        if child_content.strip():
            # 각 줄을 4칸 들여쓰기
            indented_content = "\n".join(
                "    " + line for line in child_content.split("\n")
            )
            child_contents.append(indented_content)

    # 각 child block 사이에 <br />\n 추가
    return (
        "<br />\n" + f"<br />\n".join(child_contents) + "<br />\n"
        if child_contents
        else ""
    )


def get_block_content(block, page_dir, category, indent_level=0):
    """블록 데이터를 Markdown 형식으로 변환

    Args:
        block: Notion block 데이터
        page_dir: 페이지 디렉토리
        indent_level: 현재 들여쓰기 레벨 (기본값: 0)
    """
    block_type = block.get("type")
    block_data = block.get(block_type, {})

    if block_type == "numbered_list_item":
        list_counter["numbered"] += 1
    else:
        reset_list_counter()

    # 핸들러 매핑
    handlers = {
        "paragraph": lambda: handle_paragraph(block_data) or "",
        "heading_1": lambda: handle_heading(block_data, 1) or "",
        "heading_2": lambda: handle_heading(block_data, 2) or "",
        "heading_3": lambda: handle_heading(block_data, 3) or "",
        "bulleted_list_item": lambda: handle_list_item(block_data, "-", None),
        "numbered_list_item": lambda: handle_list_item(
            block_data, "numbered", list_counter["numbered"], indent_level
        ),
        "quote": lambda: handle_quote(block_data),
        "code": lambda: handle_code(block_data),
        "image": lambda: handle_image(block_data, category, page_dir),
        "callout": lambda: handle_callout(block_data),
        "to_do": lambda: handle_to_do(block_data),
        "divider": lambda: handle_divider(block_data),
        # "toggle": lambda: handle_toggle(block_data, page_dir),
        # "table": lambda: handle_table(block_data, block.get("id")) or "",
    }

    handler = handlers.get(block_type)
    if handler:
        try:
            content = handler()
            # child blocks 처리
            if block.get("has_children", False):
                content += handle_child_block(block, page_dir, category, indent_level)
            # 블록 간 구분을 위해 항상 <br />로 개행 추가
            return content.rstrip() + "<br />\n"
        except Exception as e:
            print(f"Error processing block of type '{block_type}': {e}")
            return f"[{block_type.upper()} BLOCK ERROR]<br />\n"
    else:
        return f"[{block_type.upper()} BLOCK NOT SUPPORTED]<br />\n"
