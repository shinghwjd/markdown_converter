import streamlit as st
import tempfile
import os

# 페이지 기본 설정
st.set_page_config(
    page_title="문서 마크다운 통합 변환기",
    page_icon="📑",
    layout="centered"
)

st.title("📄마크다운 변환기")
st.caption("문서 유형에 맞는 변환 방식을 선택해 AI 입력용 마크다운(.md)으로 변환하세요.")

# 탭으로 일반 문서용과 논문용 분리
tab1, tab2 = st.tabs(["⚡ 일반 문서 변환", "📑 논문/연구자료 변환"])

# -------------------------------------------------------------
# TAB 1: 일반 문서 변환 (MarkItDown - 초고속 처리)
# -------------------------------------------------------------
with tab1:
    st.subheader("일반 보고서 / 기획서 / 이미지")
    st.info("단일 단락 문서, 표, 오피스 파일 등을 텍스트로 추출합니다.")
    
    file_general = st.file_uploader(
        "파일 업로드 (PDF, PNG, JPG, DOCX, XLSX)",
        type=["pdf", "png", "jpg", "docx", "xlsx"],
        key="uploader_general"
    )
    
    if file_general is not None:
        file_ext = os.path.splitext(file_general.name)[1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp_file:
            tmp_file.write(file_general.read())
            tmp_path = tmp_file.name

        with st.spinner("마크다운 변환 중..."):
            try:
                from markitdown import MarkItDown
                md = MarkItDown()
                result = md.convert(tmp_path)
                md_text = result.text_content

                st.success("✅ 변환 완료!")
                st.text_area("변환 결과 (클릭 후 Ctrl+A -> 복사)", md_text, height=320, key="text_general")
                st.download_button(
                    label="📥 .md 파일 다운로드",
                    data=md_text,
                    file_name=f"{os.path.splitext(file_general.name)[0]}.md",
                    mime="text/markdown",
                    key="down_general"
                )
            except Exception as e:
                st.error(f"변환 중 오류가 발생했습니다: {e}")
            finally:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)

# -------------------------------------------------------------
# TAB 2: 논문/학술자료 변환 (Docling - 2단 레이아웃/수식/주석 순서 보존)
# -------------------------------------------------------------
with tab2:
    st.subheader("학술 논문 / 학회지 / 수식 포함 PDF")
    st.info("2단(2-column) 본문 흐름, 수식(LaTeX), 표, 그림-주석(Figure) 순서를 보존합니다.")
    
    file_paper = st.file_uploader(
        "논문 PDF 업로드",
        type=["pdf"],
        key="uploader_paper"
    )
    
    if file_paper is not None:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            tmp_file.write(file_paper.read())
            tmp_path = tmp_file.name

        with st.spinner("논문 레이아웃 및 캡션 순서 정밀 분석 중 ..."):
            try:
                from docling.document_converter import DocumentConverter
                converter = DocumentConverter()
                result = converter.convert(tmp_path)
                md_paper_text = result.document.export_to_markdown()

                st.success("✅ 논문 구조 분석 및 변환 완료!")
                st.text_area("변환 결과 (클릭 후 Ctrl+A -> 복사)", md_paper_text, height=350, key="text_paper")
                st.download_button(
                    label="📥 .md 파일 다운로드",
                    data=md_paper_text,
                    file_name=f"{os.path.splitext(file_paper.name)[0]}_paper.md",
                    mime="text/markdown",
                    key="down_paper"
                )
            except Exception as e:
                st.error(f"논문 변환 중 오류가 발생했습니다: {e}")
            finally:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
