import os
import glob
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma

load_dotenv()

PDF_FOLDER = "Data"
PERSIST_DIRECTORY = "./chroma_db"

# Load PDF Documents
# ----------------------------
def load_documents():
    pdf_files = glob.glob(os.path.join(PDF_FOLDER, "*.pdf"))
    all_docs = []

    for pdf_file in pdf_files:
        loader = PyPDFLoader(pdf_file)
        docs = loader.load()

        source_name = os.path.splitext(os.path.basename(pdf_file))[0]

        for doc in docs:
            doc.metadata["source_policy"] = source_name

        all_docs.extend(docs)

    return all_docs



# ----------------------------
# Chunk Documents
# ----------------------------
def chunk_documents(documents):
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=100
    )
    return text_splitter.split_documents(documents)


# ----------------------------
# Build Vector Database (Run Once)
# ----------------------------
def build_vector_database():
    print("Creating vector database...")

    documents = load_documents()
    chunked_docs = chunk_documents(documents)

    embedding_model = OpenAIEmbeddings(
        model="text-embedding-3-small"
    )

    vectorstore = Chroma.from_documents(
        documents=chunked_docs,
        embedding=embedding_model,
        persist_directory=PERSIST_DIRECTORY
    )

    print("Vector database created successfully.")
    return vectorstore


if __name__ == "__main__":
    if not os.path.exists(PERSIST_DIRECTORY):
        build_vector_database()
    else:
        print("Vector database already exists.")