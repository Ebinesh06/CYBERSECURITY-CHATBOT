import os
from pathlib import Path

from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import SentenceTransformerEmbeddings
from langchain_community.vectorstores import Chroma


DATA_DIR = "./data"
DB_DIR = "./db"


def load_documents():
    documents = []
    path = Path(DATA_DIR)

    if not path.exists():
        print("❌ data folder not found")
        return documents

    for file in path.glob("*.txt"):
        loader = TextLoader(str(file), encoding="utf-8")
        documents.extend(loader.load())

    print(f"✅ Loaded {len(documents)} documents")
    return documents


def split_documents(documents):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=300,
        chunk_overlap=50
    )
    chunks = splitter.split_documents(documents)
    print(f"✅ Created {len(chunks)} chunks")
    return chunks


def create_db(chunks):
    embedding = SentenceTransformerEmbeddings(
        model_name="all-MiniLM-L6-v2"
    )

    db = Chroma.from_documents(
        chunks,
        embedding,
        persist_directory=DB_DIR
    )

    db.persist()
    print("✅ Vector DB created successfully!")


def main():
    os.makedirs(DB_DIR, exist_ok=True)

    docs = load_documents()
    if not docs:
        return

    chunks = split_documents(docs)
    create_db(chunks)


if __name__ == "__main__":
    main()