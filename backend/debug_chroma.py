import chromadb

CHROMA_DIR = "../db/chroma"

client = chromadb.PersistentClient(path=CHROMA_DIR)

collection = client.get_or_create_collection("DepartmentLLM")

count = collection.count()
print("📦 Total documents in collection:", count)

if count == 0:
    print("❌ Collection is EMPTY")
else:
    results = collection.get(limit=10)
    for i in range(len(results["documents"])):
        print("\n--- DOCUMENT", i + 1, "---")
        print("TEXT:", results["documents"][i][:200])
        print("METADATA:", results["metadatas"][i])
