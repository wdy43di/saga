# ~/saga/saga-core/modules/saga_lore.py
import os
from langchain_ollama import OllamaEmbeddings
from langchain_community.vectorstores import Chroma

# Paths
BASE_DIR = os.path.expanduser("~/saga/saga-core/memory")
VECTOR_DB_DIR = os.path.join(BASE_DIR, "vector_store")
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")

class LoreVault:
    def __init__(self):
        self.embeddings = OllamaEmbeddings(model="llama3", base_url=OLLAMA_URL)
        self.db = None
        self.load_vault()

    def load_vault(self):
        if os.path.exists(VECTOR_DB_DIR):
            self.db = Chroma(
                persist_directory=VECTOR_DB_DIR, 
                embedding_function=self.embeddings
            )
            print(f"📖 Lore Vault Loaded: {VECTOR_DB_DIR}")
        else:
            print("⚠️ Lore Vault not found. Running in generic mode.")

    def search(self, query, k=3):
        if not self.db:
            return ""
        # Look up the top 'k' most relevant fragments
        results = self.db.similarity_search(query, k=k)
        return "\n".join([doc.page_content for doc in results])
