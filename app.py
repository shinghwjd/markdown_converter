import streamlit as st
import fitz  # PyMuPDF
import os
import io
import re
import zipfile

# 페이지 설정
st.set_page_config(
    page_title="논문 마크다운 변환기",
    page_icon="📑",
    layout="centered"
)

# 문장 종결 부호 검사 함수
def split_incomplete_sentence(text: str):
    """
    페이지 끝이 완전한 문장으로 끝나지 않으면 마지막 미완성 문장을 분리하여 반환.
    (반환값: 해당 페이지 본문, 다음 페이지로 넘길 미완성 문장)
    """
    clean_text = text.strip()
    if not clean_text:
        return "", ""
    
    # 일반적인 문장 종결 부호: 마침표, 물음표, 느낌표, 콜론, 닫는 따옴표/괄호 뒤의 마침표
    sentence_endings = ('.', '!', '?', ':', '."', '.\'', '.)', '.]')
    
    # 마지막 문자가 종결 부호로 끝나면 그대로 반환
    if clean_text.endswith(sentence_endings):
        return clean_text, ""
    
    # 마지막 종결 부호 위치 탐색
    last_end_pos = -1
    for match in re.finditer(r'[\.\!\?][\s\n]+', clean_text):
        last_end_pos = match.end()
    
    if last_end_pos != -1:
        complete_part = clean_text[:last_end_pos].strip()
        carryover_part = clean_text[last_end_pos:].strip()
        return complete_part, carryover_part
    else:
        # 페이지 전체에 종결 부호가 없는 극단적인 경우 통째로 이월 방지(현재 페이지 유지)
        return clean_text, ""

# Figure/Table 캡션 및 본문 블록 정렬 함수
def extract_page_markdown(page):
    """
    페이지 내 텍스트 블록을 y축(위->아래) 기준으로 정렬하고,
    Figure / Table 캡션 서식을 마크다운 블록으로 정리
    """
    blocks = page.get_text("blocks")
    # 블록 좌표 (x0, y0, x1, y1, text, block_no, block_type)
    # y0(상단 위치)을 기준으로 정렬하여 읽는 순서 보정
    sorted_blocks = sorted(blocks, key=lambda b: (b[1], b[0]))
    
    page_md_lines = []
    for b in sorted_blocks:
        b_text = b[4].strip()
        if not b_text:
            continue
        
        # Figure / Fig. / Table 캡션 정렬 감지
        if re.match(r'^(Figure|Fig\.|Table)\s*\d+[:\.]?', b_text, re.IGNORECASE):
            # 캡션은 마크다운 인용구 형태로 강조 및 구분
            page_md_lines.append(f"\n> **{b_text}**\n")
        else:
            page_md_lines.append(b_text)
            
    return "\n\n".join(page_md_lines)

# UI 화면
st.title("📑 논문 마크다운 변환기")
st.caption("PDF 논문을 업로드하면 마크다운(ZIP)으로 변환합니다.")

# 전체 리셋 버튼
if st.button("🔄 화면 초기화"):
    st.session_state.clear()
    st.rerun()

uploaded_file = st.file_uploader(
    "논문 PDF 파일을 업로드하세요", 
    type=["pdf"],
    key="paper_uploader"
)

if uploaded_file is not None:
    # 원본 파일명 (확장자 제외)
    base_name = os.path.splitext(uploaded_file.name)[0]
    
    try:
        # PDF 문서 로드
        doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
        total_pages = len(doc)
        st.write(f"📖 총 **{total_pages}** 페이지가 감지되었습니다.")
        
        if st.button(f"🚀 {total_pages}페이지 마크다운 변환 시작"):
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            page_files = []  # (파일명, 마크다운 내용)
            carryover_sentence = ""  # 이전 페이지에서 넘어온 미완성 문장 조각
            
            # 페이지 넘버링 자릿수 결정 (100페이지 이상이면 3자리 001, 이하면 2자리 01)
            num_padding = max(2, len(str(total_pages)))
            
            for page_idx in range(total_pages):
                page_num = page_idx + 1
                status_text.text(f"⏳ ({page_num}/{total_pages}) 페이지 분석 및 Figure 정렬 중...")
                progress_bar.progress(page_num / total_pages)
                
                page = doc[page_idx]
                raw_page_text = extract_page_markdown(page)
                
                # 미완성 문장 분리 로직
                # 마지막 페이지는 뒤로 넘기지 않고 모두 출력
                if page_idx < total_pages - 1:
                    current_page_text, next_carryover = split_incomplete_sentence(raw_page_text)
                else:
                    current_page_text = raw_page_text
                    next_carryover = ""
                
                # 이전 페이지에서 넘어온 미완성 문장이 있다면 본문 최상단에 결합
                final_content = []
                if carryover_sentence:
                    final_content.append(f"{carryover_sentence} ")
                if current_page_text:
                    final_content.append(current_page_text)
                
                page_md_content = "".join(final_content)
                carryover_sentence = next_carryover  # 다음 루프로 이월
                
                # 파일명 생성: xxx_01.md, xxx_02.md ...
                padded_num = str(page_num).zfill(num_padding)
                output_filename = f"{base_name}_{padded_num}.md"
                
                # 헤더 정보 추가
                header = f"# {base_name} - Page {padded_num}\n\n"
                full_page_markdown = header + page_md_content.strip() + "\n"
                
                page_files.append((output_filename, full_page_markdown))
                
            doc.close()
            progress_bar.progress(1.0)
            status_text.text(f"✅ 총 {total_pages}개 페이지 변환 완료!")
            st.success("🎉 모든 페이지의 마크다운 파일 생성이 완료되었습니다.")
            
            # ZIP 압축 파일 생성
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                for file_name, content in page_files:
                    zip_file.writestr(file_name, content.encode('utf-8'))
            
            zip_buffer.seek(0)
            zip_download_name = f"{base_name}_pages_markdown.zip"
            
            # ZIP 다운로드 버튼
            st.download_button(
                label="📥 페이지별 마크다운 전체 다운로드 (ZIP)",
                data=zip_buffer,
                file_name=zip_download_name,
                mime="application/zip",
                help="모든 페이지가 개별 .md 파일로 패키징되어 있습니다."
            )
            
            # 1페이지 미리보기 제공
            if page_files:
                first_name, first_content = page_files[0]
                with st.expander(f"👀 첫 번째 페이지({first_name}) 미리보기"):
                    st.text_area("미리보기", first_content, height=250)
                    
    except Exception as e:
        st.error(f"❌ 변환 중 오류가 발생했습니다: {e}")
        st.info("새로고침 버튼을 눌러 다시 시도해 주세요.")
