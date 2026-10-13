import streamlit as st
import tempfile
import os
import io
from pypdf import PdfReader, PdfWriter

# 페이지 기본 설정
st.set_page_config(
    page_title="문서 변환 및 분할 도구",
    page_icon="📚",
    layout="centered"
)

st.title("📚 문서 변환 & PDF 분할 도구")
st.caption("전공책/논문 분할부터 AI 입력용 마크다운(.md) 변환까지 한 곳에서 처리하세요.")

# 3개의 탭 구성
tab1, tab2, tab3 = st.tabs([
    "⚡ 일반 문서 변환", 
    "📑 논문/전공책 변환 (구조 보존)", 
    "✂️ PDF 페이지 분할"
])

# -------------------------------------------------------------
# TAB 1: 일반 문서 변환 (MarkItDown - 초고속)
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
                st.text_area("변환 결과 (클릭 후 Ctrl+A -> 복사)", md_text, height=300, key="text_general")
                st.download_button(
                    label="📥 .md 파일 다운로드",
                    data=md_text,
                    file_name=f"{os.path.splitext(file_general.name)[0]}.md",
                    mime="text/markdown",
                    key="down_general"
                )
            except Exception as e:
                st.error(f"변환 실패: {e}")
            finally:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)

# -------------------------------------------------------------
# TAB 2: 논문 / 전공책 챕터 변환 (Docling - 레이아웃 보존)
# -------------------------------------------------------------
with tab2:
    st.subheader("학술 논문 / 전공책 단원 (수식, 2단 단락)")
    st.info("2단 편집 순서, LaTeX 수식, 표, 그림 캡션을 원본 흐름대로 추출합니다. (10~30페이지 권장)")
    
    file_paper = st.file_uploader(
        "분할된 전공책 챕터나 논문 PDF 업로드",
        type=["pdf"],
        key="uploader_paper"
    )
    
    if file_paper is not None:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            tmp_file.write(file_paper.read())
            tmp_path = tmp_file.name

        with st.spinner("문서 구조 및 캡션 순서 정밀 분석 중 ..."):
            try:
                from docling.document_converter import DocumentConverter
                converter = DocumentConverter()
                result = converter.convert(tmp_path)
                md_paper_text = result.document.export_to_markdown()

                st.success("✅ 정밀 변환 완료!")
                st.text_area("변환 결과 (클릭 후 Ctrl+A -> 복사)", md_paper_text, height=350, key="text_paper")
                st.download_button(
                    label="📥 .md 파일 다운로드",
                    data=md_paper_text,
                    file_name=f"{os.path.splitext(file_paper.name)[0]}_parsed.md",
                    mime="text/markdown",
                    key="down_paper"
                )
            except Exception as e:
                st.error(f"변환 실패: {e}")
            finally:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)

# -------------------------------------------------------------
# TAB 3: PDF 페이지 분할 (자르기)
# -------------------------------------------------------------
with tab3:
    st.subheader("대용량 PDF / 전공책 페이지 자르기")
    st.info("필요한 챕터(예: 45~70페이지)만 잘라내어 새 PDF로 만듭니다.")
    
    file_to_split = st.file_uploader(
        "자르고 싶은 원본 PDF 업로드",
        type=["pdf"],
        key="uploader_split"
    )
    
    if file_to_split is not None:
        try:
            reader = PdfReader(file_to_split)
            total_pages = len(reader.pages)
            st.write(f"📖 **총 페이지 수:** `{total_pages}` 쪽")
            
            # 페이지 범위 입력 (슬라이더 또는 숫자 입력)
            col1, col2 = st.columns(2)
            with col1:
                start_page = st.number_input("시작 페이지", min_value=1, max_value=total_pages, value=1)
            with col2:
                end_page = st.number_input("끝 페이지", min_value=start_page, max_value=total_pages, value=min(start_page + 19, total_pages))
            
            if st.button("✂️ 선택 범위 잘라내기"):
                with st.spinner("PDF 분할 중..."):
                    writer = PdfWriter()
                    # 0-indexed 처리 (start_page - 1 부터 end_page 까지)
                    for page_idx in range(start_page - 1, end_page):
                        writer.add_page(reader.pages[page_idx])
                    
                    # 메모리 버퍼에 저장
                    output_stream = io.BytesIO()
                    writer.write(output_stream)
                    output_stream.seek(0)
                    
                    split_filename = f"{os.path.splitext(file_to_split.name)[0]}_p{start_page}-{end_page}.pdf"
                    
                    st.success(f"✅ {start_page}쪽 ~ {end_page}쪽 분할 완료! ({end_page - start_page + 1}페이지)")
                    st.download_button(
                        label="📥 잘라낸 PDF 다운로드",
                        data=output_stream,
                        file_name=split_filename,
                        mime="application/pdf"
                    )
                    st.caption("💡 다운로드받은 파일을 바로 '2번째 탭(논문/전공책 변환)'에 넣으시면 됩니다.")
        except Exception as e:
            st.error(f"PDF를 읽는 중 오류가 발생했습니다: {e}")
