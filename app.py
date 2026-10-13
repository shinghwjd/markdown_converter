import streamlit as st
import tempfile
import os
import io
import math
import zipfile
from pypdf import PdfReader, PdfWriter

# 페이지 기본 설정
st.set_page_config(
    page_title="문서 변환 및 분할 도구",
    page_icon="📚",
    layout="centered"
)

# -------------------------------------------------------------
# 에러 발생 시 안전하게 새로고침/초기화하는 함수
# -------------------------------------------------------------
def handle_error_with_refresh(err_msg: str, key_suffix: str = ""):
    st.error(f"❌ 오류가 발생했습니다: {err_msg}")
    st.info("파일 손상, 형식 불일치 또는 메모리 부족일 수 있습니다. 아래 버튼을 눌러 초기화해 보세요.")
    if st.button("🔄 페이지 새로고침 및 초기화", key=f"btn_refresh_{key_suffix}"):
        st.session_state.clear()
        st.rerun()

st.title("📚 AI 문서 변환 & PDF 분할 도구")
st.caption("전공책/논문 분할부터 다중 PDF 순차 마크다운 변환까지 한 곳에서 처리하세요.")

# 상단 리셋 버튼
col_head, col_btn = st.columns([4, 1])
with col_btn:
    if st.button("🔄 전체 리셋", help="모든 작업과 업로드 상태를 초기화합니다."):
        st.session_state.clear()
        st.rerun()

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
    st.subheader("일반 보고서 / 기획서 / 단일 문서")
    st.info("단일 문서, 표, 오피스 파일 등을 1~3초 만에 텍스트로 빠르게 추출합니다.")
    
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
                st.text_area("변환 결과 (클릭 후 Ctrl+A -> 복사)", md_text, height=300, key="text_general")
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
# TAB 2: 논문 / 전공책 다중 순차 변환 (Docling - 레이아웃 보존)
# -------------------------------------------------------------
with tab2:
    st.subheader("파일 순차 변환")
    st.info("PDF를 한 번에 올리면 통합 파일 또는 ZIP으로 제공합니다.")
    
    files_paper = st.file_uploader(
        " PDF 파일을 선택해 업로드하세요 (복수 선택 가능)",
        type=["pdf"],
        accept_multiple_files=True,
        key="uploader_paper_multi"
    )
    
    if files_paper:
        # 파일명을 기준으로 가나다/숫자 오름차순 정렬 (part1, part2 순서 보장)
        sorted_files = sorted(files_paper, key=lambda f: f.name)
        total_files = len(sorted_files)
        
        st.write(f"📁 총 **{total_files}개**의 파일이 선택되었습니다:")
        file_names_preview = ", ".join([f"`{f.name}`" for f in sorted_files[:5]])
        if total_files > 5:
            file_names_preview += f" 외 {total_files - 5}개"
        st.caption(file_names_preview)
        
        if st.button(f"🚀 {total_files}개 파일 순차 변환 시작"):
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            combined_markdown = []
            individual_results = []  # (filename, content)
            
            from docling.document_converter import DocumentConverter
            converter = DocumentConverter()
            
            has_error = False
            for idx, file_obj in enumerate(sorted_files):
                current_num = idx + 1
                status_text.text(f"⏳ ({current_num}/{total_files}) '{file_obj.name}' 변환 중...")
                progress_bar.progress(idx / total_files)
                
                tmp_path = None
                try:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                        tmp_file.write(file_obj.read())
                        tmp_path = tmp_file.name
                    
                    # 변환 실행
                    result = converter.convert(tmp_path)
                    md_text = result.document.export_to_markdown()
                    
                    # 개별 및 결합 버퍼에 추가
                    base_name = os.path.splitext(file_obj.name)[0]
                    individual_results.append((f"{base_name}.md", md_text))
                    
                    combined_markdown.append(f"\n\n<!-- ==================== {file_obj.name} ==================== -->\n\n")
                    combined_markdown.append(md_text)
                    
                except Exception as e:
                    has_error = True
                    handle_error_with_refresh(f"'{file_obj.name}' 처리 중 오류: {e}", f"tab2_{idx}")
                    break
                finally:
                    if tmp_path and os.path.exists(tmp_path):
                        os.remove(tmp_path)
            
            if not has_error:
                progress_bar.progress(1.0)
                status_text.text(f"✅ 총 {total_files}개 파일 모두 변환 완료!")
                st.success("🎉 모든 분할 파일의 마크다운 변환이 끝났습니다.")
                
                full_combined_text = "".join(combined_markdown)
                
                # 결과 다운로드 옵션 제공
                col_d1, col_d2 = st.columns(2)
                
                # 1. 하나의 통합 마크다운으로 받기
                with col_d1:
                    st.download_button(
                        label="📄 통합 마크다운(.md) 다운로드",
                        data=full_combined_text,
                        file_name="combined_all_chapters.md",
                        mime="text/markdown",
                        help="모든 분할 파일의 내용을 순서대로 이어붙인 단일 파일입니다."
                    )
                
                # 2. 개별 마크다운 ZIP으로 받기
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
                        mime="application/zip",
                        help="각 챕터/파트별로 분리된 .md 파일들이 들어있는 압축 파일입니다."
                    )
                
                with st.expander("👀 통합 마크다운 미리보기 (앞부분 2,000자)"):
                    st.text(full_combined_text[:2000] + ("\n\n... (생략) ..." if len(full_combined_text) > 2000 else ""))

# -------------------------------------------------------------
# TAB 3: PDF 페이지 분할 (직접 범위 지정 vs 전체 N분할)
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
            else:
                n_parts = st.number_input(
                    "몇 개(N)의 파일로 나눌까요?", 
                    min_value=2, 
                    max_value=min(50, total_pages), 
                    value=min(5, total_pages),
                    help="예: 500쪽 책을 5개로 나누면 약 100쪽씩 5개 파일로 생성됩니다."
                )
                
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
                        
        except Exception as e:
            handle_error_with_refresh(str(e), "tab3")
