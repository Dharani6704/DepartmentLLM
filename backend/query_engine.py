# # query_engine.py
# """
# Query pipeline:
# - Embed user query
# - Retrieve top-k most similar chunks from chroma
# - Assemble a prompt with retrieved context
# - Call Llama3 via Ollama-compatible HTTP API
# - Save conversation messages via provided conv storage hooks (the app will call)
# """
#query_engine.py

# import os
# import re
# import json
# from typing import List, Dict, Optional
# import requests
# from sentence_transformers import SentenceTransformer
# import chromadb
# from chromadb.config import Settings

# # Config
# BASE_DIR = os.path.dirname(os.path.dirname(__file__))  # Go one level up to DepartmentLLM
# CHROMA_DIR = os.path.join(BASE_DIR, "db", "chroma")
# #CHROMA_DIR = os.environ.get("CHROMA_DB_DIR", "./db/chroma")
# EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
# OLLAMA_API_URL = os.environ.get("OLLAMA_API_URL", "http://localhost:11434")
# OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3")
# TOP_K = int(os.environ.get("RETRIEVE_TOP_K", 20))

# # Setup
# embedder = SentenceTransformer(EMBEDDING_MODEL)
# client = chromadb.PersistentClient(path=CHROMA_DIR)
# #client = chromadb.Client(Settings(chroma_db_impl="duckdb+parquet", persist_directory=CHROMA_DIR))
# collection = client.get_collection("DepartmentLLM")

# def detect_doc_type_from_query(query: str) -> str | None:
#     q = query.lower()

#     if "conference paper" in q or "conference papers" in q:
#         return "conference_paper"

#     if "journal" in q or "journals" in q:
#         return "journal_paper"

#     if "event" in q or "workshop" in q or "guest lecture" in q or "visit" in q:
#         return "event"

#     return None


# def retrieve_similar_chunks(query: str, k: int = TOP_K) -> List[Dict]:
#     if k is None:
#         k = TOP_K
#     q_emb = embedder.encode(query, convert_to_numpy=True).tolist()
#     # chroma query: return list of matches with ids/documents/metadatas
#     results = collection.query(query_embeddings=[q_emb], n_results=k, include=["documents","metadatas","distances"])
#     docs = []
#     filtered=[]
#     # results format: dict with lists
#     if not results or len(results.get("documents", [])) == 0:
#         return []
#     docs_list = results["documents"][0]
#     metas = results["metadatas"][0]
#     dists = results.get("distances", [[]])[0]
#     for doc, meta, dist in zip(docs_list, metas, dists):
#         filtered.append({
#         "text": doc,
#         "meta": meta,
#         "distance": round(float(dist), 4)
#     })

# # sort by distance and take top-k (lowest = most similar)
#     filtered = sorted(filtered, key=lambda x: x["distance"])[:k]
#     return filtered


#     # for doc, meta, dist in zip(docs_list, metas, dists):
#     #     if any(word.lower() in doc.lower() for word in query.split()):
#     #         filtered.append({"text": doc, "meta": meta, "distance": round(float(dist),4)})
#     # return filtered[:k]
#     #     docs.append({"text": doc, "meta": meta, "distance": round(float(dist),4)})
#     # return docs
# # def detect_intent(query: str):
# #     q = query.lower()

# #     if "event" in q:
# #         return "event"
# #     if "journal" in q:
# #         return "journal"
# #     if "paper" in q:
# #         return "paper"
# #     if "timetable" in q:
# #         return "timetable"
# #     return "general"


# # # def filtered_search(query, intent):
# # #     where = {}

# # #     if intent != "general":
# # #         where["doc_type"] = intent

# # #     year_match = re.search(r"(19|20)\d{2}", query)
# # #     if year_match:
# # #         where["year"] = year_match.group(0)

# # #     authors_match = re.search(r"by\s+(.*)", query.lower())
# # #     if authors_match:
# # #         where["authors"] = {"$contains": authors_match.group(1)}

# # #     results = collection.get(where=where)

# # #     return results

# # def filtered_search(query, intent):
# #     where = {}

# #     q = query.lower()

# #     # intent filter
# #     if intent != "general":
# #         where["doc_type"] = intent

# #     # year
# #     if year_match := re.search(r"(19|20)\d{2}", q):
# #         where["year"] = year_match.group(0)

# #     # coordinator / author detection
# #     if "by" in q or "coordinator" in q or "conducted" in q:
# #         name = re.sub(r".*by|coordinator|conducted by", "", q).strip()
# #         name = name.split("in")[0].strip()
# #         where["coordinators"] = {"$contains": name}

# #     print("DEBUG WHERE FILTER:", where)

# #     return collection.get(where=where, include=["metadatas","documents"])


# # def decide_output_mode(query):
# #     q = query.lower()

# #     if "list" in q and "event" in q:
# #         return "event_names"
# #     if "coordinator" in q:
# #         return "coordinators"
# #     if "paper" in q or "journal" in q:
# #         return "titles_only"
# #     return "full"

# def retrieve_candidates(query: str, k: int = 300):
#     q_emb = embedder.encode(query, convert_to_numpy=True).tolist()
#     res = collection.query(
#         query_embeddings=[q_emb],
#         n_results=k,
#         include=["documents", "metadatas"]
#     )

#     docs = []
#     for doc, meta in zip(res["documents"][0], res["metadatas"][0]):
#         docs.append({"text": doc, "meta": meta})
#     return docs

# def filter_events(rows, person=None, year=None):
#     results = []

#     EVENT_WORDS = [
#         "event", "workshop", "seminar", "fdp",
#         "training", "hands on", "visit", "guest lecture"
#     ]

#     for r in rows:
#         text = r["text"].lower()

#         if year and year not in text:
#             continue

#         if person and person.lower() not in text:
#             continue

#         if not any(w in text for w in EVENT_WORDS):
#             continue

#         results.append(r)

#     return results


# def format_response(items, mode):

#     if not items:
#         return "Not Available"

#     if mode == "event_names":
#         return "\n".join(f"• {i.get('event_name','')}" for i in items)

#     if mode == "coordinators":
#         return "\n".join(f"• {i.get('coordinators','')}" for i in items)

#     if mode == "titles_only":
#         return "\n".join(f"• {i.get('title', i.get('text',''))}" for i in items)

#     return "\n\n".join(i.get("text","") for i in items)


# def build_prompt(user_query: str, contexts: List[Dict], instruction: Optional[str] = None) -> str:
#     """
#     Build a precise, structured, and user-friendly prompt for Llama3.
#     Ensures accuracy for events by year, coordinator, club, etc.
#     """

#     # Combine retrieved context
#     context_text = "\n\n".join(
#         [
#             f"[{i+1}] (Source: {c.get('meta', {}).get('source_file', 'unknown')}, chunk {c.get('meta', {}).get('chunk_index', -1)})\n{c['text']}"
#             for i, c in enumerate(contexts)
#         ]
#     )

#     prompt = f"""
# You are a data retrieval assistant for college records.
# Use only the retrieved context below to answer the user's question accurately and completely.

# ### Context:
# {context_text}

# ### Task:
# 1. Read the user’s question carefully.
# 2. Search the above context for exact matches — same year, same coordinator name, or same event title.
# 3. If the user specifies a year (e.g., 2022), include **only events from that year**.
# 4. If the user specifies a person (e.g., "events by Sunanda"), list **all events coordinated by that person**, regardless of year.
# 5. If multiple events match, list all of them neatly in a structured format:
#    - Event Name  
#    - Date or Year  
#    - Coordinator(s)  
#    - Drive link (if available)

# 6. If no relevant data is found, respond only with: "Not Available"
# 7. If the user only asks for *event names*, list only the event titles as bullet points without extra info.
# 8. Always format your answer in markdown for clarity.

# ### Output format:
# Use clean, human-readable formatting — either a bulleted list or a simple table.
# Avoid unnecessary explanations or assumptions.

# ### User Question:
# {user_query}

# ### Answer:
# """
#     return prompt.strip()

# # def build_prompt(user_query: str, contexts: List[Dict], instruction: Optional[str] = None) -> str:
# #     """
# #     Builds a precise, context-driven prompt that adapts automatically to user intent.
# #     Handles queries like:
# #       - 'events conducted by Devika'
# #       - 'event names in 2024'
# #       - 'list events with drive link'
# #     """
# #     context_text = "\n\n".join(
# #         [
# #             f"[{i+1}] (Source: {c.get('meta', {}).get('source_file', 'unknown')}, chunk {c.get('meta', {}).get('chunk_index', -1)})\n{c['text']}"
# #             for i, c in enumerate(contexts)
# #         ]
# #     )

# #     prompt = f"""
# # You are a factual retrieval assistant for a college event database.
# # Use **only** the provided context below. Do not invent data.

# # ### Context:
# # {context_text}

# # ### Task:
# # 1. Read the user's question carefully.
# # 2. Extract only facts directly mentioned in the context.
# # 3. When listing events:
# #    - Event Name  
# #    - Date or Year  
# #    - Coordinator(s)  
# #    - Drive link (if available)
# # 4. If multiple events match (by year or coordinator), include all.
# # 5. If the user says "event names", list **only** the names, one per line.
# # 6. If the data truly doesn't exist, reply only with: "Not Available".
# # 7. Keep the output simple and human-readable. Avoid extra commentary.

# # ### User Query:
# # {user_query}

# # ### Answer:
# # """
# #     return prompt.strip()


# def call_llama(prompt: str, max_tokens: int = 512, temperature: float = 0.0) -> str:
#     """
#     Call a local Ollama-like API. The exact request body may need adjustment depending on your local server.
#     This function assumes the server accepts a POST to {OLLAMA_API_URL}/api/generate or similar.
#     If your server uses another contract, adapt here.
#     """
#     # Build a request body compatible with Ollama v0.6+ / common patterns
#     url = OLLAMA_API_URL.rstrip("/") + "/api/generate"
#     body = {
#         "model": OLLAMA_MODEL,
#         "prompt": prompt,
#         "max_tokens": max_tokens,
#         "temperature": temperature,
#         # instruct to return plain text
#         "stream": False
#     }
#     try:
#         resp = requests.post(url, json=body, timeout=60)
#         resp.raise_for_status()
#         data = resp.json()
#         # Ollama-like responses often contain 'response' or 'text' fields. We try the common spots:
#         # 
#         if isinstance(data, dict):
#             if "choices" in data:  # OpenAI-style
#                 return data["choices"][0]["message"]["content"].strip()
#             if "response" in data:
#                 return data["response"].strip()
#             if "text" in data:
#                 return data["text"].strip()

#         return json.dumps(data, indent=2)
#     except Exception as e:
#         # return helpful message for debugging
#         return f"[LLM call failed: {e}]"

# # def answer_query(user_query: str, conversation_id: Optional[str] = None, top_k: int = TOP_K) -> Dict:
# #     """
# #     Full pipeline:
# #     - retrieve similar chunks
# #     - build prompt
# #     - call llama
# #     - return answer plus contexts used
# #     """
# #     contexts = retrieve_similar_chunks(user_query, k=top_k)
# #     prompt = build_prompt(user_query, contexts)
# #     llm_answer = call_llama(prompt)
# #     # Clean up excessive markdown or extra commentary
# #     llm_answer = llm_answer.replace("###", "").replace("**", "").strip()

# # # Ensure minimal structure
# #     if not any(x in llm_answer.lower() for x in ["event", "coordinator", "not available"]):
# #         llm_answer = "Not Available"

    
# #     # Pretty-format context preview for readability
# #     formatted_contexts = [
# #         {
# #             "source_file": c.get("meta", {}).get("source_file", "unknown"),
# #             "chunk_index": c.get("meta", {}).get("chunk_index", -1),
# #             "distance": c.get("distance", 0),
# #             "excerpt": (c["text"][:120] + "...") if len(c["text"]) > 120 else c["text"]
# #         }
# #         for c in contexts
# #     ]

# #     return {
# #         "query": user_query,
# #         "answer": llm_answer,
# #         "contexts_used": formatted_contexts,
# #         "total_contexts": len(formatted_contexts)
# #     }
# #     # return {
# #     #     "query": user_query,
# #     #     "answer": llm_answer,
# #     #     "context_used": contexts,
# #     # }


# # def answer_query(user_query: str, conversation_id: Optional[str] = None, top_k: int = TOP_K) -> Dict:
# #     """
# #     Full pipeline:
# #     1. Detect intent (event / paper / journal / timetable / general)
# #     2. Try metadata-filtered search first
# #     3. Fallback to semantic search if no results
# #     4. Format response based on output mode
# #     """

# #     intent = detect_intent(user_query)
# #     mode = decide_output_mode(user_query)

# #     # 🔍 1 — Metadata-filtered search
# #     try:
# #         items = filtered_search(user_query, intent)
# #     except Exception as e:
# #         items = {"documents": [], "metadatas": []}

# #     # 🔁 2 — Fallback to semantic similarity search if nothing found
# #     if not items or len(items.get("documents", [])) == 0:
# #         items = retrieve_similar_chunks(user_query, k=top_k)
# #         # Chroma-like structure expected for format_response
# #         # Wrap results in 'documents'/'metadatas' format
# #         if items and isinstance(items, list):
# #             items = {
# #                 "documents": [i["text"] for i in items],
# #                 "metadatas": [i.get("meta", {}) for i in items]
# #             }

# #     # 🔧 3 — Normalize items for format_response
# #     results = []
# #     for doc, meta in zip(items.get("documents", []), items.get("metadatas", [])):
# #         results.append({"text": doc, **meta})

# #     # 🧾 4 — Format final response
# #     response_text = format_response(results, mode)

# #     return {
# #         "query": user_query,
# #         "answer": response_text,
# #         "total_results": len(results)
# #     }

# # def answer_query(user_query: str, top_k: int = 300):
# #     rows = retrieve_candidates(user_query, k=top_k)

# #     year = re.search(r"(19|20)\d{2}", user_query)
# #     year = year.group(0) if year else None

# #     person = None
# #     if "by" in user_query.lower() or "conducted" in user_query.lower():
# #         person = user_query.lower().split("by")[-1].strip()

# #     events = filter_events(rows, person=person, year=year)

# #     if not events:
# #         return {"answer": "Not Available", "total": 0}

# #     # ONLY event names if user asked list
# #     if "list" in user_query.lower():
# #         names = []
# #         for e in events:
# #             names.append(e["text"].split("  ")[0])
# #         return {
# #             "answer": "\n".join(f"• {n}" for n in names),
# #             "total": len(names)
# #         }

# #     return {
# #         "answer": "\n\n".join(e["text"] for e in events),
# #         "total": len(events)
# #     }

# def hard_filtered_search(doc_type=None, person=None, year=None):
#     filters = []

#     if doc_type:
#         filters.append({"doc_type": doc_type})

#     if person:
#         filters.append({"person": {"$contains": person.title()}})

#     if year:
#         filters.append({"year": year})

#     if not filters:
#         where = {}
#     elif len(filters) == 1:
#         where = filters[0]
#     else:
#         where = {"$and": filters}

#     results = collection.get(
#         where=where,
#         include=["documents", "metadatas"]
#     )

#     rows = []
#     for doc, meta in zip(results["documents"], results["metadatas"]):
#         rows.append({"text": doc, "meta": meta})

#     return rows

# def answer_query(user_query: str):
#     q = user_query.lower()

#     # -------- intent detection --------
#     doc_type = None
#     if "conference" in q:
#         doc_type = "conference_paper"
#     elif "journal" in q:
#         doc_type = "journal_paper"
#     elif "event" in q or "workshop" in q:
#         doc_type = "event"

#     # -------- person --------
#     person = None
#     if m := re.search(r"by\s+([a-z.\s]+)(?:\s+in|\s+\d{4}|$)", q):
#         person = m.group(1).strip()

#     # -------- year --------
#     year = None
#     if m := re.search(r"(19|20)\d{2}", q):
#         year = m.group(0)

#     # -------- HARD FILTER (NO EMBEDDINGS) --------
#     rows = hard_filtered_search(
#         doc_type=doc_type,
#         person=person,
#         year=year
#     )

#     if not rows:
#         return {"answer": "Not Available", "total": 0}

#     # -------- output --------
#     answer = "\n".join(f"• {r['text']}" for r in rows)

#     return {
#         "answer": answer,
#         "total": len(rows)
#     }
  


# # Example usage
# if __name__ == "__main__":
#     q = "When is the next AI workshop in the college?"
#     result = answer_query(q)
#     print(json.dumps(result, indent=2, ensure_ascii=False))
# #    print(out["answer"])



# # 
# query_engine.py

import os
import re
import json
from typing import List, Dict, Optional
import requests
from sentence_transformers import SentenceTransformer
import chromadb

# ================= CONFIG ================= #

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
CHROMA_DIR = os.path.join(BASE_DIR, "db", "chroma")

EMBEDDING_MODEL = "all-MiniLM-L6-v2"
OLLAMA_API_URL = "http://localhost:11434"
OLLAMA_MODEL = "llama3"
TOP_K = 300

# ================= SETUP ================= #

embedder = SentenceTransformer(EMBEDDING_MODEL)
client = chromadb.PersistentClient(path=CHROMA_DIR)
collection = client.get_collection("DepartmentLLM")

# ================= RETRIEVE ================= #

def retrieve_candidates(query: str, k: int = TOP_K):
    q_emb = embedder.encode(query, convert_to_numpy=True).tolist()
    res = collection.query(
        query_embeddings=[q_emb],
        n_results=k,
        include=["documents", "metadatas"]
    )

    docs = []
    for doc, meta in zip(res["documents"][0], res["metadatas"][0]):
        docs.append({"text": doc, "meta": meta})
    return docs


# ================= FILTERING ================= #

def fallback_filter(rows, person=None, year=None, doc_type=None):
    results = []

    for r in rows:
        text = r["text"].lower()

        # filter by person
        if person and person.lower() not in text:
            continue

        # filter by year
        if year and year not in text:
            continue

        # filter by document type
        if doc_type:
            if doc_type == "event" and not any(x in text for x in ["event", "workshop", "seminar", "lecture", "visit"]):
                continue
            if doc_type == "journal" and "journal" not in text:
                continue
            if doc_type == "conference" and "conference" not in text:
                continue

        results.append(r)

    return results


# ================= DEDUPLICATION ================= #

def deduplicate(rows):
    seen = set()
    unique = []
    for r in rows:
        title = r["text"].split("|")[1].strip() if "|" in r["text"] else r["text"]
        if title not in seen:
            seen.add(title)
            unique.append(r)
    return unique


# ================= PROMPT BUILDER ================= #

def build_prompt(query, contexts):
    context_text = "\n".join([c["text"] for c in contexts])

    return f"""
You are a college data retrieval assistant.

Use ONLY the provided context to answer.

Context:
{context_text}

User question: {query}

Rules:
- List matching items clearly.
- If nothing matches, reply only: Not Available
"""


# ================= LLM CALL ================= #

def call_llama(prompt):
    url = OLLAMA_API_URL + "/api/generate"
    body = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "temperature": 0,
        "stream": False
    }

    try:
        resp = requests.post(url, json=body, timeout=60)
        return resp.json().get("response", "").strip()
    except Exception as e:
        return f"LLM ERROR: {e}"


# ================= MAIN PIPELINE ================= #

def answer_query(user_query: str):
    rows = retrieve_candidates(user_query)

    q = user_query.lower()

    # detect year
    year = re.search(r"(19|20)\d{2}", q)
    year = year.group(0) if year else None

    # detect person
    person = None
    if "by" in q:
        person = q.split("by")[-1].strip()
    elif "conducted by" in q:
        person = q.split("conducted by")[-1].strip()
    elif "sunanda" in q:
        person = "sunanda"
    elif "subash" in q:
        person = "subash"

    # detect doc type
    doc_type = None
    if "event" in q:
        doc_type = "event"
    elif "journal" in q:
        doc_type = "journal"
    elif "conference" in q:
        doc_type = "conference"

    # filter rows
    filtered = fallback_filter(rows, person=person, year=year, doc_type=doc_type)
    filtered = deduplicate(filtered)

    if not filtered:
        return {"answer": "Not Available", "total": 0}

    # If user asked LIST -> print bullet list
    if "list" in q:
        output = []
        for f in filtered:
            output.append("• " + f["text"])
        return {"answer": "\n".join(output), "total": len(filtered)}

    # else full LLM answer
    prompt = build_prompt(user_query, filtered)
    answer = call_llama(prompt)

    return {"answer": answer, "total": len(filtered)}
