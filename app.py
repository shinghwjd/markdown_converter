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

# 기본 제공 AI 번역 프롬프트 템플릿
PROMPT_TEMPLATE = """아래 제공된 마크다운 논문 텍스트를 한국어로 번역하되, PDF 파싱 오류를 수정한 깔끔한 마크다운 문서로 다시 작성해줘.

[작업 조건]:
1. **수식 복원**: 쪼개진 시그마(∑), 적분, 첨자, 수식 번호([1] 등)를 결합하여 올바른 인라인($...$) 또는 블록($$...$$) LaTeX 문법으로 정리할 것.
2. **서식 유지**: 제목(#), 인용구(>), 목록(-), 표(|) 구조는 누락 없이 유지할 것.
3. **용어 유지**: 수식 기호, 변수명(MI, 𝐼b, 𝜎, 𝜏 등)은 원문 그대로 유지하고 본문만 매끄러운 한국어 학술체로 번역할 것.
4. 인사말이나 부연 설명 없이, 오직 완성된 결과만 출력할 것."""

# 문장 종결 부호 검사 함수
def split_incomplete_sentence(text: str):
    clean_text = text.strip()
    if not clean_text:
        return "", ""
    
    sentence_endings = ('.', '!', '?', ':', '."', '.\'', '.)', '.]')
    if clean_text.endswith(sentence_endings):
        return clean_text, ""
    
    last_end_pos = -1
    for match in re.finditer(r'[\.\!\?][\s\n]+', clean_text):
        last_end_pos = match.end()
    
    if last_end_pos != -1:
        complete_part = clean_text[:last_end_pos].strip()
        carryover_part = clean_text[last_end_pos:].strip()
        return complete_part, carryover_part
    else:
        return clean_text, ""

# Figure/Table 캡션 및 본문 블록 정렬 함수
def extract_page_markdown(page):
    blocks = page.get_text("blocks")
    # y0(위쪽) 기준 정렬
    sorted_blocks = sorted(blocks, key=lambda b: (b[1], b[0]))
    
    page_md_lines = []
    for b in sorted_blocks:
        b_text = b[4].strip()
        if not b_text:
            continue
        
        # Figure / Fig. / Table 캡션 정렬 감지
        if re.match(r'^(Figure|Fig\.|Table)\s*\d+[:\.]?', b_text, re.IGNORECASE):
            page_md_lines.append(f"\n> **{b_text}**\n")
        else:
            page_md_lines.append(b_text)
            
    return "\n\n".join(page_md_lines)

# ---------------- UI 화면 ----------------
st.title("📑 논문 마크다운 변환기")
st.caption("PDF 논문을 페이지별 마크다운으로 분할 변환하고, 프롬프트를 함께 제공합니다.")

# 전체 리셋 버튼
if st.button("🔄 화면 초기화"):
    st.session_state.clear()
    st.rerun()

# 💡 추천 AI 번역/해석 프롬프트 박스 (접이식 아코디언)
with st.expander("📋 [추천] 수식 복원 & 한국어 번역 프롬프트 (클릭하여 복사)", expanded=True):
    st.markdown("변환된 `.md` 파일을 AI(ChatGPT, Claude, Gemini 등)에 첨부할 때 **아래 프롬프트를 함께 복사해 입력**하세요:")
    # 우측 상단에 원클릭 복사 아이콘이 생성되는 code 블록
    st.code(PROMPT_TEMPLATE, language="markdown")

st.divider()

# 파일 업로드
uploaded_file = st.file_uploader(
    "논문 PDF 파일을 업로드하세요", 
    type=["pdf"],
    key="paper_uploader"
)

if uploaded_file is not None:
    base_name = os.path.splitext(uploaded_file.name)[0]
    
    try:
        doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
        total_pages = len(doc)
        st.write(f"📖 총 **{total_pages}** 페이지가 감지되었습니다.")
        
        if st.button(f"🚀 {total_pages}페이지 마크다운 변환 시작"):
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            page_files = []
            carryover_sentence = ""
            num_padding = max(2, len(str(total_pages)))
            
            for page_idx in range(total_pages):
                page_num = page_idx + 1
                status_text.text(f"⏳ ({page_num}/{total_pages}) 페이지 분석 및 Figure 정렬 중...")
                progress_bar.progress(page_num / total_pages)
                
                page = doc[page_idx]
                raw_page_text = extract_page_markdown(page)
                
                # 미완성 문장 이월 처리
                if page_idx < total_pages - 1:
                    current_page_text, next_carryover = split_incomplete_sentence(raw_page_text)
                else:
                    current_page_text = raw_page_text
                    next_carryover = ""
                
                final_content = []
                if carryover_sentence:
                    final_content.append(f"{carryover_sentence} ")
                if current_page_text:
                    final_content.append(current_page_text)
                
                page_md_content = "".join(final_content)
                carryover_sentence = next_carryover
                
                # 파일명 생성: xxx_01.md, xxx_02.md ...
                padded_num = str(page_num).zfill(num_padding)
                output_filename = f"{base_name}_{padded_num}.md"
                
                header = f"# {base_name} - Page {padded_num}\n\n"
                full_page_markdown = header + page_md_content.strip() + "\n"
                page_files.append((output_filename, full_page_markdown))
                
            doc.close()
            progress_bar.progress(1.0)
            status_text.text(f"✅ 총 {total_pages}개 페이지 변환 완료!")
            st.success("🎉 모든 페이지의 마크다운 파일 생성이 완료되었습니다.")
            
            # ZIP 압축
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
                mime="application/zip"
            )
            
            # 1페이지 미리보기
            if page_files:
                first_name, first_content = page_files[0]
                with st.expander(f"👀 첫 번째 페이지({first_name}) 미리보기"):
                    st.text_area("미리보기 내용", first_content, height=250)
                    
    except Exception as e:
        st.error(f"❌ 변환 중 오류가 발생했습니다: {e}")
        st.info("새로고침 버튼을 눌러 다시 시도해 주세요.")
