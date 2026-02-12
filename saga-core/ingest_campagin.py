import os
from langchain_community.document_loaders import PyPDFLoader, DirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import OllamaEmbeddings
from langchain_community.vectorstores import Chroma

# --- PATHS ---
UPLOAD_DIR = "/saga/memory/uploads"
VECTOR_DB_DIR = "/saga/memory/vector_store"
OLLAMA_URL = "http://saga-ollama:11434"

def digest():
    print("📖 Scribe is opening the scrolls...")
    
    # 1. Load PDFs from the directory
    loader = DirectoryLoader(UPLOAD_DIR, glob="./*.pdf", loader_cls=PyPDFLoader)
    docs = loader.load()
    print(f"✅ Loaded {len(docs)} pages of lore.")

    # 2. Split text into manageable chunks
    # We use 1000 characters with 100 overlap so context isn't lost at the edges
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    splits = text_splitter.split_documents(docs)
    print(f"✂️ Split lore into {len(splits)} fragments.")

    # 3. Create Embeddings (The mathematical "meaning" of the text)
    embeddings = OllamaEmbeddings(model="llama3", base_url=OLLAMA_URL)

    # 4. Store in ChromaDB
    print("💎 Crystallizing knowledge into the Vector Vault (this takes time)...")
    vectorstore = Chroma.from_documents(
        documents=splits, 
        embedding=embeddings, 
        persist_directory=VECTOR_DB_DIR
    )
    print("🔥 THE INGESTION IS COMPLETE. Saga now knows your world.")

if __name__ == "__main__":
    digest()
