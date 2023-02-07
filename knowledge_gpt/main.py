import time
import math
import streamlit as st
from utils import (
    parse_docx,
    parse_pdf,
    parse_txt,
    search_docs,
    embed_docs,
    text_to_docs,
    get_answer,
    get_sources,
    wrap_text_in_html,
)
from openai.error import OpenAIError


def clear_submit():
    st.session_state["submit"] = False


def set_openai_api_key(api_key: str):
    st.session_state["OPENAI_API_KEY"] = api_key


st.set_page_config(page_title="DocDiscovery", page_icon="📚", layout="wide")
st.header("📚DocDiscovery")

with st.sidebar:
    st.markdown("# 关于应用")
    st.markdown(
        "📚DocDiscovery 可以让你使用自然语言对你的文档提出问题并且获得回答"
    )
    st.markdown("---")
    st.markdown(
        "## 如何使用\n"
        "1. 在下方输入框输入你的 [Key](https://platform.openai.com/account/api-keys) \n"
        "2. 上传pdf/doc/txt文件\n"
        "3. 等待应用解析文件\n"
        "4. 解析完成即可提问"
    )
    api_key_input = st.text_input(
        "OpenAI API Key",
        type="password",
        placeholder="输入你的OpenAI Key (sk-...)",
        help="You can get your API key from https://platform.openai.com/account/api-keys.",
        value=st.session_state.get("OPENAI_API_KEY", ""),
    )

    if api_key_input:
        set_openai_api_key(api_key_input)

    st.markdown("---")
    st.markdown("如果没有OpenAI API key，请联系@Tao")

uploaded_file = st.file_uploader(
    "Upload a pdf, docx, or txt file",
    type=["pdf", "docx", "txt"],
    help="Scanned documents are not supported yet!",
    on_change=clear_submit,
)

index = None
doc = None
if uploaded_file is not None:
    if uploaded_file.name.endswith(".pdf"):
        doc = parse_pdf(uploaded_file)
    elif uploaded_file.name.endswith(".docx"):
        doc = parse_docx(uploaded_file)
    elif uploaded_file.name.endswith(".txt"):
        doc = parse_txt(uploaded_file)
    else:
        raise ValueError("File type not supported!")
    text = text_to_docs(doc)
    try:
        rpm = 20
        minutes = math.ceil(len(text)/rpm)
        with st.spinner(f'Estimated {minutes} minutes wait to process the file'):
            index = embed_docs(text, rpm)
        st.success('Done!')

        st.session_state["api_key_configured"] = True
    except OpenAIError as e:
        st.error(e._message)

query = st.text_area("Ask a question about the document", on_change=clear_submit)
with st.expander("Advanced Options"):
    show_all_chunks = st.checkbox("Show all chunks retrieved from vector search")
    show_full_doc = st.checkbox("Show parsed contents of the document")

if show_full_doc and doc:
    with st.expander("Document"):
        # Hack to get around st.markdown rendering LaTeX
        st.markdown(f"<p>{wrap_text_in_html(doc)}</p>", unsafe_allow_html=True)

button = st.button("Submit")
if button or st.session_state.get("submit"):
    if not st.session_state.get("api_key_configured"):
        st.error("Please configure your OpenAI API key!")
    elif not index:
        st.error("Please upload a document!")
    elif not query:
        st.error("Please enter a question!")
    else:
        st.session_state["submit"] = True
        # Output Columns
        answer_col, sources_col = st.columns(2)
        sources = search_docs(index, query)

        try:
            answer = get_answer(sources, query)
            if not show_all_chunks:
                # Get the sources for the answer
                sources = get_sources(answer, sources)

            with answer_col:
                st.markdown("#### Answer")
                st.markdown(answer["output_text"].split("SOURCES: ")[0])

            with sources_col:
                st.markdown("#### Sources")
                for source in sources:
                    st.markdown(source.page_content)
                    st.markdown(source.metadata["source"])
                    st.markdown("---")

        except OpenAIError as e:
            st.error(e._message)
