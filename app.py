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

st.title("📚문서 변환 & PDF 분할 도구")
st.caption("전공책/논문 분할부터 마크다운(.md) 변환까지 한 곳에서 처리하세요.")

# 3개의 탭 구성
tab1, tab2, tab3 = st.tabs([
    "⚡ 일반 문서 변환", 
    "📑 논문/전공책 변환", 
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

        with st.spinner("문서 구조 및 캡션 순서 정밀 분석 중 (약 20~40초 소요)..."):
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
# TAB 3: PDF 페이지 분할 (직접 범위 지정 vs N분할)
# -------------------------------------------------------------
with tab3:
    st.subheader("대용량 PDF / 전공책 분할")
    st.info("원하는 구간만 잘라내거나, 전체 PDF를 N개 파일로 균등 분할하여 ZIP으로 받습니다.")
    
    file_to_split = st.file_uploader(
        "분할할 원본 PDF 업로드",
        type=["pdf"],
        key="uploader_split"
    )
    
    if file_to_split is not None:
        try:
            reader = PdfReader(file_to_split)
            total_pages = len(reader.pages)
            base_filename = os.path.splitext(file_to_split.name)[0]
            st.write(f"📖 **총 페이지 수:** `{total_pages}` 쪽")
            
            # 분할 방식 선택 라디오 버튼
            split_mode = st.radio(
                "분할 방식을 선택하세요",
                ["📌 원하는 구간 지정 분할 (단일 파일)", "📦 전체 N등분 균등 분할 (ZIP 압축)"],
                horizontal=True
            )
            
            # ---------------------------------------------------------
            # 모드 1: 원하는 구간 지정
            # ---------------------------------------------------------
            if split_mode == "📌 원하는 구간 지정 분할 (단일 파일)":
                col1, col2 = st.columns(2)
                with col1:
                    start_page = st.number_input("시작 페이지", min_value=1, max_value=total_pages, value=1)
                with col2:
                    end_page = st.number_input(
                        "끝 페이지", 
                        min_value=start_page, 
                        max_value=total_pages, 
                        value=min(start_page + 19, total_pages)
                    )
                
                if st.button("✂️ 선택 구간 자르기"):
                    with st.spinner("PDF 분할 중..."):
                        writer = PdfWriter()
                        for p in range(start_page - 1, end_page):
                            writer.add_page(reader.pages[p])
                        
                        out_stream = io.BytesIO()
                        writer.write(out_stream)
                        out_stream.seek(0)
                        
                        out_name = f"{base_filename}_p{start_page}-{end_page}.pdf"
                        st.success(f"✅ {start_page}쪽 ~ {end_page}쪽 분할 완료! (총 {end_page - start_page + 1}쪽)")
                        st.download_button(
                            label="📥 잘라낸 PDF 다운로드",
                            data=out_stream,
                            file_name=out_name,
                            mime="application/pdf"
                        )
            
            # ---------------------------------------------------------
            # 모드 2: 전체 N등분 균등 분할
            # ---------------------------------------------------------
            else:
                n_parts = st.number_input(
                    "몇 개(N)의 파일로 나눌까요?", 
                    min_value=2, 
                    max_value=min(50, total_pages), 
                    value=min(5, total_pages),
                    help="예: 500쪽 책을 5개로 나누면 약 100쪽씩 5개 파일로 생성됩니다."
                )
                
                # 분할 미리보기 계산
                import math
                import zipfile
                pages_per_part = math.ceil(total_pages / n_parts)
                st.caption(f"💡 파일 1개당 약 **{pages_per_part}쪽** 내외로 총 **{n_parts}개**의 PDF가 생성됩니다.")
                
                if st.button(f"📦 전체 {n_parts}분할 시작 및 ZIP 생성"):
                    with st.spinner(f"PDF를 {n_parts}개로 나누어 압축 중..."):
                        zip_stream = io.BytesIO()
                        
                        with zipfile.ZipFile(zip_stream, "w", zipfile.ZIP_DEFLATED) as zip_file:
                            for i in range(n_parts):
                                start_idx = i * pages_per_part
                                end_idx = min((i + 1) * pages_per_part, total_pages)
                                
                                if start_idx >= total_pages:
                                    break
                                
                                part_writer = PdfWriter()
                                for p in range(start_idx, end_idx):
                                    part_writer.add_page(reader.pages[p])
                                
                                pdf_buffer = io.BytesIO()
                                part_writer.write(pdf_buffer)
                                pdf_buffer.seek(0)
                                
                                part_filename = f"{base_filename}_part{i+1}_p{start_idx+1}-{end_idx}.pdf"
                                zip_file.writestr(part_filename, pdf_buffer.getvalue())
                        
                        zip_stream.seek(0)
                        zip_filename = f"{base_filename}_{n_parts}parts.zip"
                        
                        st.success(f"✅ 총 {n_parts}개 파일로 분할 및 압축 완료!")
                        st.download_button(
                            label="📥 분할된 전체 PDF 압축파일(.zip) 다운로드",
                            data=zip_stream,
                            file_name=zip_filename,
                            mime="application/zip"
                        )
                        st.caption("💡 압축을 푼 뒤 필요한 챕터 파일을 바로 변환 탭에 넣어 사용하세요.")
                        
        except Exception as e:
            st.error(f"PDF 처리 중 오류 발생: {e}")
