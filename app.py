import streamlit as st
import tempfile
import os
import io
import math
import zipfile
import fitz  # PyMuPDF (메모리를 거의 차지하지 않는 초경량/고속 파서)
from pypdf import PdfReader, PdfWriter

# 페이지 기본 설정
st.set_page_config(
    page_title="문서 변환 및 분할 도구",
    page_icon="📚",
    layout="centered"
)

# 에러 복구 함수
def handle_error_with_refresh(err_msg: str, key_suffix: str = ""):
    st.error(f"❌ 오류 발생: {err_msg}")
    st.info("아래 버튼을 눌러 상태를 새로고침하세요.")
    if st.button("🔄 새로고침 및 초기화", key=f"btn_refresh_{key_suffix}"):
        st.session_state.clear()
        st.rerun()

st.title("📚문서 변환 & PDF 분할 도구")
st.caption("PDF/문서를 AI 입력용 마크다운(.md)으로 빠르고 가볍게 변환합니다.")

col_head, col_btn = st.columns([4, 1])
with col_btn:
    if st.button("🔄 전체 리셋"):
        st.session_state.clear()
        st.rerun()

tab1, tab2, tab3 = st.tabs([
    "⚡ 일반 문서 변환", 
    "📑 논문/전공책 순차 변환", 
    "✂️ PDF 페이지 분할"
])

# -------------------------------------------------------------
# TAB 1: 일반 문서 변환 (MarkItDown)
# -------------------------------------------------------------
with tab1:
    st.subheader("일반 보고서 / 기획서 / 단일 문서")
    file_general = st.file_uploader(
        "파일 업로드 (PDF, PNG, JPG, DOCX, XLSX)",
        type=["pdf", "png", "jpg", "docx", "xlsx"],
        key="uploader_general"
    )
    
    if file_general is not None:
        file_ext = os.path.splitext(file_general.name)[1]
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp_file:
                tmp_file.write(file_general.read())
                tmp_path = tmp_file.name

            with st.spinner("마크다운 변환 중..."):
                from markitdown import MarkItDown
                md = MarkItDown()
                result = md.convert(tmp_path)
                md_text = result.text_content

                st.success("✅ 변환 완료!")
                st.text_area("변환 결과 (복사 가능)", md_text, height=300, key="text_general")
                st.download_button(
                    label="📥 .md 파일 다운로드",
                    data=md_text,
                    file_name=f"{os.path.splitext(file_general.name)[0]}.md",
                    mime="text/markdown",
                    key="down_general"
                )
        except Exception as e:
            handle_error_with_refresh(str(e), "tab1")
        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.remove(tmp_path)

# -------------------------------------------------------------
# TAB 2: 논문 / 전공책 다중 순차 변환 (경량 PyMuPDF 기반)
# -------------------------------------------------------------
with tab2:
    st.subheader("논문 & 분할된 전공책 순차 변환")
    st.info("여러 개의 PDF를 순서대로 가볍고 빠르게 마크다운으로 변환합니다.")
    
    files_paper = st.file_uploader(
        "PDF 파일들을 업로드하세요 (복수 선택 가능)",
        type=["pdf"],
        accept_multiple_files=True,
        key="uploader_paper_multi"
    )
    
    if files_paper:
        sorted_files = sorted(files_paper, key=lambda f: f.name)
        total_files = len(sorted_files)
        st.write(f"📁 총 **{total_files}개** 파일 준비 완료")
        
        if st.button(f"🚀 {total_files}개 파일 순차 변환 시작"):
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            combined_markdown = []
            individual_results = []
            has_error = False
            
            for idx, file_obj in enumerate(sorted_files):
                current_num = idx + 1
                status_text.text(f"⏳ ({current_num}/{total_files}) '{file_obj.name}' 변환 중...")
                progress_bar.progress(idx / total_files)
                
                try:
                    # PyMuPDF로 메모리 부담 없이 순차 파싱
                    doc = fitz.open(stream=file_obj.read(), filetype="pdf")
                    text_parts = [f"# {file_obj.name}\n\n"]
                    
                    for page_num in range(len(doc)):
                        page = doc[page_num]
                        page_text = page.get_text("text")
                        text_parts.append(f"## Page {page_num + 1}\n\n{page_text}\n\n")
                    
                    doc.close()
                    md_text = "".join(text_parts)
                    
                    base_name = os.path.splitext(file_obj.name)[0]
                    individual_results.append((f"{base_name}.md", md_text))
                    combined_markdown.append(f"\n\n<!-- ===== {file_obj.name} ===== -->\n\n" + md_text)
                    
                except Exception as e:
                    has_error = True
                    handle_error_with_refresh(f"'{file_obj.name}' 오류: {e}", f"tab2_{idx}")
                    break
            
            if not has_error:
                progress_bar.progress(1.0)
                status_text.text(f"✅ 총 {total_files}개 변환 완료!")
                st.success("🎉 모든 파일 변환이 성공적으로 완료되었습니다.")
                
                full_combined_text = "".join(combined_markdown)
                col_d1, col_d2 = st.columns(2)
                with col_d1:
                    st.download_button(
                        label="📄 통합 마크다운(.md) 다운로드",
                        data=full_combined_text,
                        file_name="combined_all_chapters.md",
                        mime="text/markdown"
                    )
                with col_d2:
                    zip_buffer = io.BytesIO()
                    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                        for md_name, content in individual_results:
                            zip_file.writestr(md_name, content)
                    zip_buffer.seek(0)
                    st.download_button(
                        label="📦 개별 마크다운 압축(.zip) 다운로드",
                        data=zip_buffer,
                        file_name="converted_markdowns.zip",
                        mime="application/zip"
                    )

# -------------------------------------------------------------
# TAB 3: PDF 페이지 분할
# -------------------------------------------------------------
with tab3:
    st.subheader("대용량 PDF / 전공책 분할")
    file_to_split = st.file_uploader("분할할 원본 PDF 업로드", type=["pdf"], key="uploader_split")
    
    if file_to_split is not None:
        try:
            reader = PdfReader(file_to_split)
            total_pages = len(reader.pages)
            base_filename = os.path.splitext(file_to_split.name)[0]
            st.write(f"📖 **총 페이지 수:** `{total_pages}` 쪽")
            
            split_mode = st.radio(
                "분할 방식을 선택하세요",
                ["📌 원하는 구간 지정 분할 (단일 파일)", "📦 전체 N등분 균등 분할 (ZIP 압축)"],
                horizontal=True
            )
            
            if split_mode == "📌 원하는 구간 지정 분할 (단일 파일)":
                col1, col2 = st.columns(2)
                with col1:
                    start_page = st.number_input("시작 페이지", min_value=1, max_value=total_pages, value=1)
                with col2:
                    end_page = st.number_input("끝 페이지", min_value=start_page, max_value=total_pages, value=min(start_page + 19, total_pages))
                
                if st.button("✂️ 선택 구간 자르기"):
                    with st.spinner("PDF 분할 중..."):
                        writer = PdfWriter()
                        for p in range(start_page - 1, end_page):
                            writer.add_page(reader.pages[p])
                        out_stream = io.BytesIO()
                        writer.write(out_stream)
                        out_stream.seek(0)
                        
                        st.success(f"✅ {start_page}쪽 ~ {end_page}쪽 분할 완료!")
                        st.download_button(
                            label="📥 잘라낸 PDF 다운로드",
                            data=out_stream,
                            file_name=f"{base_filename}_p{start_page}-{end_page}.pdf",
                            mime="application/pdf"
                        )
            else:
                n_parts = st.number_input("몇 개(N)의 파일로 나눌까요?", min_value=2, max_value=min(50, total_pages), value=min(5, total_pages))
                pages_per_part = math.ceil(total_pages / n_parts)
                st.caption(f"💡 파일 1개당 약 **{pages_per_part}쪽** 내외로 분할됩니다.")
                
                if st.button(f"📦 전체 {n_parts}분할 시작 및 ZIP 생성"):
                    with st.spinner("PDF 분할 및 압축 중..."):
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
                                zip_file.writestr(f"{base_filename}_part{i+1}_p{start_idx+1}-{end_idx}.pdf", pdf_buffer.getvalue())
                        
                        zip_stream.seek(0)
                        st.success(f"✅ 총 {n_parts}개 파일 분할 및 압축 완료!")
                        st.download_button(
                            label="📥 전체 PDF 압축파일(.zip) 다운로드",
                            data=zip_stream,
                            file_name=f"{base_filename}_{n_parts}parts.zip",
                            mime="application/zip"
                        )
        except Exception as e:
            handle_error_with_refresh(str(e), "tab3")
