import os
import sys

# 프로젝트 루트의 'notion_lambda' 폴더 경로를 sys.path에 추가
# 이렇게 하면 해당 폴더 내부의 모듈을 절대 경로로 임포트할 수 있게 됨
lambda_source_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "notion_lambda")
)
sys.path.insert(0, lambda_source_path)
