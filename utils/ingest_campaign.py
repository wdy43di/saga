import os
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_ollama import OllamaEmbeddings
from langchain_community.vectorstores import Chroma

# --- CONFIG ---
BASE_DIR = os.path.expanduser("~/saga/saga-core/memory")
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
VECTOR_DB_DIR = os.path.join(BASE_DIR, "vector_store")
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
BATCH_SIZE = 20 # Increased for better efficiency

def digest():
    print("\n[🛡️  SCRIBE RESUMING - INTELLIGENT MODE]")

    # WE REMOVED THE SHUTIL.RMTREE (No more deleting!)
    os.makedirs(VECTOR_DB_DIR, exist_ok=True)

    pdf_files = [f for f in os.listdir(UPLOAD_DIR) if f.endswith('.pdf')]
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)

    embeddings = OllamaEmbeddings(
        model="llama3",
        base_url=OLLAMA_URL,
        client_kwargs={"timeout": 900}
    )

    # Initialize the database connection first
    vectorstore = Chroma(
        persist_directory=VECTOR_DB_DIR,
        embedding_function=embeddings
    )

    # Get existing IDs so we don't repeat work
    existing_ids = set()
    try:
        # We peek at the IDs already in the vault
        data = vectorstore.get()
        existing_ids = set(data['ids'])
        print(f"📜 Found {len(existing_ids)} fragments already etched in the vault.")
    except Exception:
        print("📜 Vault appears new or empty. Starting fresh.")

    all_splits = []
    for pdf in pdf_files:
        path = os.path.join(UPLOAD_DIR, pdf)
        print(f"📖 Parsing: {pdf}...")
        try:
            loader = PyPDFLoader(path)
            docs = loader.load()
            splits = text_splitter.split_documents(docs)
            
            # UNIQUE ID LOGIC: Create a unique ID based on filename and chunk index
            for i, split in enumerate(splits):
                custom_id = f"{pdf}_{i}"
                if custom_id not in existing_ids:
                    split.metadata["id"] = custom_id
                    all_splits.append(split)
            
            print(f"  └─ {len(splits)} fragments total. {len(all_splits)} are new.")
        except Exception as e:
            print(f"  └─ ❌ Error: {e}")

    total_new = len(all_splits)
    if total_new > 0:
        print(f"\n💎 Crystallizing {total_new} NEW fragments...")
        for i in range(0, total_new, BATCH_SIZE):
            batch = all_splits[i : i + BATCH_SIZE]
            ids = [s.metadata["id"] for s in batch]
            try:
                vectorstore.add_documents(documents=batch, ids=ids)
                percent = ((i + len(batch)) / total_new) * 100
                print(f"✅ Etched: {i + len(batch)}/{total_new} ({percent:.1f}%)")
            except Exception as e:
                print(f"⚠️ Batch failed: {e}")
        print("\n🔥 THE GREAT DIGESTION IS COMPLETE.")
    else:
        print("✅ No new fragments found. The vault is already up to date!")

if __name__ == "__main__":
    digest()
