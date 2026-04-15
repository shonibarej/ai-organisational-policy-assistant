import streamlit as st
import os
from pathlib import Path
from dotenv import load_dotenv
from build_vector_db import build_vector_database

from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_chroma import Chroma
from langchain_core.prompts import PromptTemplate


st.set_page_config(page_title="Policy Assistant", layout="centered")

load_dotenv()

PERSIST_DIRECTORY = "./chroma_db"

# Ensure Data folder exists
if not Path("Data").exists():
    st.error("Data folder not found.")
    st.stop()

# Build DB only once
if "db_built" not in st.session_state:
    if not os.path.exists(PERSIST_DIRECTORY):
        with st.spinner("Setting up knowledge base... please wait ⏳"):
            build_vector_database()
        st.success("Knowledge base ready ✅")
    st.session_state.db_built = True

# ----------------------------
# Page Config
# ----------------------------


st.title("📘 Employee Policy Assistant")
st.caption("Ask questions about organizational policies.")



# ----------------------------
# Load Vector Database
# ----------------------------
embedding_model = OpenAIEmbeddings(model="text-embedding-3-small")


vectorstore = Chroma(
    persist_directory=PERSIST_DIRECTORY,
    embedding_function=embedding_model
)

retriever = vectorstore.as_retriever(
    search_type="mmr",
    search_kwargs={
        "k": 4,
        "fetch_k": 8,
        "lambda_mult": 0.7
    }
)

# ----------------------------
# Prompt Template
# ----------------------------
TEMPLATE = """
You are an AI assistant that answers employee questions using ONLY the provided organizational policy context.

Conversation History:
{history}

Rules:
1. Use only the provided context to answer.
2. Do NOT use external knowledge.
3. If the exact information requested is not explicitly stated:
   - First say: "This information is not specified in the provided policies."
   - Then summarise any related information found in the context.
4. Use conversation history only to understand the current question.
5. Do NOT invent policy names.
6. Do NOT include a source section in your answer.

Context:
{context}

Current Question:
{question}
"""

prompt_template = PromptTemplate.from_template(TEMPLATE)

chat_model = ChatOpenAI(
    model="gpt-4.1-mini",
    temperature=0
)



# ----------------------------
# Session State (Chat History)
# ----------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])


def format_history(messages):
    history_text = ""
    for msg in messages:
        if msg["role"] == "user":
            history_text += f"User: {msg['content']}\n"
        elif msg["role"] == "assistant":
            history_text += f"Assistant: {msg['content']}\n"
    return history_text

# ----------------------------
# User Input
# ----------------------------
if prompt := st.chat_input("Ask a question about company policies..."):

    # Add user message to history
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("user"):
        st.markdown(prompt)

    # Retrieve documents (still based on current question only)
    retrieved_docs = retriever.invoke(prompt)

    context_text = "\n\n".join([doc.page_content for doc in retrieved_docs])
    sources = list(set([doc.metadata.get("source_policy") for doc in retrieved_docs]))

    # Format conversation history
    history_text = format_history(st.session_state.messages[-6:-1])  # exclude current question

    # Build final prompt
    final_prompt = prompt_template.format(
        history=history_text,
        context=context_text,
        question=prompt
    )

    response = chat_model.invoke(final_prompt)

    answer = response.content + f"\n\n**Source:** {', '.join(sources)}"

    with st.chat_message("assistant"):
        st.markdown(answer)

    st.session_state.messages.append({"role": "assistant", "content": answer})


# Sidebar
with st.sidebar:
    st.markdown("### Controls")

    if st.button("Clear Chat"):
        st.session_state.messages = []
        st.rerun()

    st.markdown("---")
    st.markdown("### Available Policies")

    # Get stored metadata from Chroma
    all_data = vectorstore.get()
    policy_names = list(set(
        meta.get("source_policy")
        for meta in all_data["metadatas"]
        if meta.get("source_policy") is not None
    ))

    policy_names.sort()

    for policy in policy_names:
        st.markdown(f"- {policy}")
