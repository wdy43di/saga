import chromadb
from chromadb.utils import embedding_functions

# 1. Define the Ollama embedding function
# This ensures we use the 4096-dimension 'brain'
ollama_ef = embedding_functions.OllamaEmbeddingFunction(
    url="http://localhost:11434/api/embeddings",
    model_name="llama3", 
)

client = chromadb.PersistentClient(path="/home/jschreck/saga/saga-core/memory/vector_store")

# 2. Get the collection using that specific embedding function
col = client.get_collection(name="langchain", embedding_function=ollama_ef)

print(f"Total fragments etched: {col.count()}")

# 3. Test Query
results = col.query(
    query_texts=["Tell me about the clans of Svilland"],
    n_results=1
)

print("\n--- Saga's Memory Result ---")
print(results['documents'][0])
