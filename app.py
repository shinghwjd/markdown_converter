import streamlit as st
from markitdown import MarkItDown
import tempfile
import os

st.set_page_config(page_title="AI 토큰 절약 마크다운 변환기", page_icon="📝", layout="centered")

st.title("📄 AI용 마크다운 변환기")
st.caption("PDF/이미지/문서를 마크다운으로 변환해 AI 토큰 소모를 최소화합니다.")

# 파일 업로드 창
uploaded_file = st.file_uploader(
    "변환할 문서를 끌어다 놓으세요 (PDF, PNG, JPG, DOCX, XLSX 지원)",
    type=["pdf", "png", "jpg", "docx", "xlsx"]
)

if uploaded_file is not None:
    file_ext = os.path.splitext(uploaded_file.name)[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp_file:
        tmp_file.write(uploaded_file.read())
        tmp_path = tmp_file.name

    with st.spinner("마크다운으로 분석 및 변환 중..."):
        try:
            md = MarkItDown()
            result = md.convert(tmp_path)
            markdown_text = result.text_content

            st.success("✅ 변환 완료!")

            # AI 전달용 텍스트 영역
            st.text_area(
                "변환 결과 (클릭 후 Ctrl+A -> Ctrl+C 로 복사)",
                markdown_text,
                height=350
            )

            # 다운로드 버튼
            st.download_button(
                label="📥 .md 파일로 다운로드",
                data=markdown_text,
                file_name=f"{os.path.splitext(uploaded_file.name)[0]}.md",
                mime="text/markdown"
            )
        except Exception as e:
            st.error(f"변환 실패: {e}")
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
