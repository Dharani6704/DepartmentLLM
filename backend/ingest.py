# # ingest.py
# import os
# import io
# from pathlib import Path
# from typing import Dict, List, Optional

# import pandas as pd
# from sentence_transformers import SentenceTransformer
# import chromadb
# from chromadb.config import Settings

# # LangChain community loaders & splitters
# from langchain_community.document_loaders import (
#     PyPDFLoader,
#     Docx2txtLoader,

#     TextLoader,
# )
# from langchain_text_splitters import RecursiveCharacterTextSplitter


# # ================================
# # CONFIG
# # ================================
# BASE_DIR = os.path.dirname(os.path.dirname(__file__))  # Go one level up to DepartmentLLM
# CHROMA_DIR = os.path.join(BASE_DIR, "db", "chroma")
# DATA_DIR = os.path.join(BASE_DIR, "data")
# #CHROMA_DIR = os.environ.get("CHROMA_DB_DIR", "./db/chroma")
# EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
# CHUNK_SIZE = int(os.environ.get("CHUNK_SIZE", 1500))
# CHUNK_OVERLAP = int(os.environ.get("CHUNK_OVERLAP", 300))

# print("📂 Using CHROMA_DIR:", CHROMA_DIR)
# print("📂 Using DATA_DIR:", os.getcwd())
# # ================================
# # SETUP
# # ================================
# embedder = SentenceTransformer(EMBEDDING_MODEL)
# client = chromadb.PersistentClient(path=CHROMA_DIR)
# #client = chromadb.Client(Settings(chroma_db_impl="duckdb+parquet", persist_directory=CHROMA_DIR))

# COLLECTION_NAME = "DepartmentLLM"
# collection = client.get_or_create_collection(COLLECTION_NAME)
# coll = client.get_collection("DepartmentLLM")
# print(coll.count())  # should show number of chunks

# # ================================
# # TABLE TO TEXT
# # ================================
# def table_to_text_chunks(df: pd.DataFrame, rows_per_chunk: int = 50) -> List[str]:
#     if df.empty:
#         return []
#     chunks = []
#     cols = list(df.columns)
#     for start in range(0, len(df), rows_per_chunk):
#         sub = df.iloc[start : start + rows_per_chunk]
#         lines = []
#         #header = " | ".join(map(str, cols))
#         #lines.append(header)
#         for _, row in sub.iterrows():
#             #lines.append(" | ".join(str(row.get(c, "")) for c in cols))
#             desc = ", ".join([f"{col.strip()}: {str(row[col]).strip()}" for col in cols])
#             lines.append(desc)
#         chunks.append("\n".join(lines))
#     return chunks    

# # ================================
# # FILE INGESTION
# # ================================
# def extract_text_from_file(file_bytes: bytes, filename: str) -> List[str]:
#     """Extract text from file using appropriate loader or pandas for structured data"""
#     ext = Path(filename).suffix.lower()
#     temp_path = f"./temp_{filename}"
#     with open(temp_path, "wb") as f:
#         f.write(file_bytes)

#     docs: List[str] = []

#     try:
#         if ext == ".pdf":
#             loader = PyPDFLoader(temp_path)
#             docs = [page.page_content for page in loader.load()]
#         elif ext in [".docx", ".doc"]:
#             loader = Docx2txtLoader(temp_path)
#             docs = [d.page_content for d in loader.load()]
#         elif ext in [".txt", ".md"]:
#             loader = TextLoader(temp_path)
#             docs = [d.page_content for d in loader.load()]
#         elif ext == ".csv":
#             df = pd.read_csv(temp_path)
#             docs = table_to_text_chunks(df)
#         elif ext in [".xlsx", ".xls"]:
#             xls = pd.read_excel(temp_path, sheet_name=None)
#             for sheet_name, df in xls.items():
#                 sheet_chunks = table_to_text_chunks(df)
#                 docs += [f"SHEET: {sheet_name}\n{chunk}" for chunk in sheet_chunks]
#         else:
#             # fallback: decode text
#             text = file_bytes.decode(errors="ignore")
#             docs = [text]
#     finally:
#         os.remove(temp_path)

#     return docs

# # ================================
# # MAIN INGEST FUNCTION
# # ================================
# def ingest_file_bytes(file_bytes: bytes, filename: str, metadata: Optional[Dict] = None) -> Dict:
#     metadata = metadata or {}
#     texts = extract_text_from_file(file_bytes, filename)

#     # Split into chunks
#     splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
#     chunks = []
#     for t in texts:
#     # Clean up unnecessary symbols, repeated newlines
#         clean_text = (
#         t.replace("–", "-")
#          .replace("•", "-")
#          .replace("  ", " ")
#          .strip()
#         )
#         if clean_text:
#             chunks += splitter.split_text(clean_text)

# # Filter out empty or duplicate chunks
#     chunks = [c.strip() for c in chunks if c.strip()]
#     chunks = list(dict.fromkeys(chunks))  # remove duplicates
#     # for t in texts:
#     #     chunks += splitter.split_text(t)

#     if not chunks:
#         return {"status": "empty", "count": 0}

#     embeddings = embedder.encode(chunks, convert_to_numpy=True, show_progress_bar=False)
#     ids = [f"{filename}_{i}" for i in range(len(chunks))]
#     metadatas = [{"source_file": filename, **metadata, "chunk_index": i} for i in range(len(chunks))]

#     collection.upsert(ids=ids, embeddings=embeddings.tolist(), documents=chunks, metadatas=metadatas)
#     #client.persist()
#     return {"status": "ok", "count": len(chunks), "sample_ids": ids[:5]}

# # ================================
# # FOLDER INGESTION
# # ================================
# def ingest_folder(folder_path: str) -> Dict:
#     allowed_exts = [".pdf", ".docx", ".doc", ".csv", ".xlsx", ".xls", ".txt", ".md"]
#     summary = {"total_chunks": 0, "files": []}
#     for f in Path(folder_path).rglob("*"):
#         if f.suffix.lower() in allowed_exts:
#             with open(f, "rb") as fh:
#                 res = ingest_file_bytes(fh.read(), f.name, metadata={"path": str(f)})
#             summary["files"].append({f.name: res})
#             summary["total_chunks"] += res.get("count", 0)
#     return summary

# if __name__ == "__main__":
#     import argparse, json
#     parser = argparse.ArgumentParser()
#     parser.add_argument("--folder", help="Folder to ingest", required=True)
#     args = parser.parse_args()
#     out = ingest_folder(args.folder)
#     print(json.dumps(out, indent=2))



# 

# #ingest.py
# import os
# from pathlib import Path
# from typing import Dict, List, Optional
# import pandas as pd
# import re
# from sentence_transformers import SentenceTransformer
# import chromadb
# from langchain_text_splitters import RecursiveCharacterTextSplitter

# # CONFIG
# BASE_DIR = os.path.dirname(os.path.dirname(__file__))
# CHROMA_DIR = os.path.join(BASE_DIR, "db", "chroma")
# DATA_DIR = os.path.join(BASE_DIR, "data")
# EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "all-MiniLM-L6-v2")

# # Tunable
# CHUNK_SIZE = int(os.environ.get("CHUNK_SIZE", 1500))
# CHUNK_OVERLAP = int(os.environ.get("CHUNK_OVERLAP", 300))
# TOP_K = int(os.environ.get("RETRIEVE_TOP_K", 20))

# print("📂 Using CHROMA_DIR:", CHROMA_DIR)
# print("📂 Using DATA_DIR:", DATA_DIR)

# # Setup
# embedder = SentenceTransformer(EMBEDDING_MODEL)
# client = chromadb.PersistentClient(path=CHROMA_DIR)
# collection = client.get_or_create_collection("DepartmentLLM")

# def clean_text(t: str) -> str:
#     if t is None:
#         return ""
#     return (
#         str(t)
#         .replace("–", "-")
#         .replace("•", "-")
#         .replace("\r", " ")
#         .replace("\t", " ")
#         .replace("\n\n", "\n")
#         .strip()
#     )

# def extract_auto_metadata_from_row(row: pd.Series) -> Dict:
#     text = " ".join([str(x) for x in row.values if pd.notna(x)])
#     meta = {}
#     year_match = re.search(r"(20\d{2})", text)
#     if year_match:
#         meta["year"] = year_match.group(1)
#     # coordinator heuristics
#     coord_match = re.search(r"Coordinator[s]?:\s*([A-Za-z0-9.,\s&()-]+)", text, re.IGNORECASE)
#     if coord_match:
#         coords = [c.strip() for c in coord_match.group(1).split(",") if c.strip()]
#         meta["coordinators"] = coords
#     # speaker heuristics
#     speaker_match = re.search(r"Speaker[s]?:\s*([A-Za-z0-9.,\s&()-]+)", text, re.IGNORECASE)
#     if speaker_match:
#         meta["speakers"] = [s.strip() for s in speaker_match.group(1).split(",") if s.strip()]
#     return meta

# def table_to_text_chunks(df: pd.DataFrame) -> List[Dict]:
#     if df.empty:
#         return []
#     chunks = []
#     cols = list(df.columns)
#     for _, row in df.iterrows():
#         pieces = []
#         for c in cols:
#             if pd.notna(row[c]):
#                 pieces.append(f"{c.strip()}: {str(row[c]).strip()}")
#         chunk_text = clean_text(", ".join(pieces))
#         meta = extract_auto_metadata_from_row(row)
#         chunks.append({"text": chunk_text, "metadata": meta})
#     return chunks

# def extract_text_from_file(file_bytes: bytes, filename: str) -> List[Dict]:
#     ext = Path(filename).suffix.lower()
#     temp_path = f"./temp_{filename}"
#     with open(temp_path, "wb") as f:
#         f.write(file_bytes)
#     docs = []
#     try:
#         if ext == ".csv":
#             df = pd.read_csv(temp_path)
#             docs = table_to_text_chunks(df)
#         elif ext in [".xlsx", ".xls"]:
#             xls = pd.read_excel(temp_path, sheet_name=None)
#             for sheet_name, df in xls.items():
#                 sheet_chunks = table_to_text_chunks(df)
#                 for c in sheet_chunks:
#                     c["metadata"]["sheet_name"] = sheet_name
#                     docs.append(c)
#         else:
#             # fallback: raw text
#             text = open(temp_path, encoding="utf-8", errors="ignore").read()
#             docs = [{"text": clean_text(text), "metadata": {}}]
#     finally:
#         try:
#             os.remove(temp_path)
#         except Exception:
#             pass
#     return docs

# def ingest_file_bytes(file_bytes: bytes, filename: str, metadata: Optional[Dict] = None) -> Dict:
#     metadata = metadata or {}
#     docs = extract_text_from_file(file_bytes, filename)
#     if not docs:
#         return {"status": "empty", "count": 0}

#     splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
#     all_text_chunks = []
#     all_metas = []
#     for d in docs:
#         text = d.get("text", "")
#         if not text:
#             continue
#         subchunks = splitter.split_text(text) if len(text) > 400 else [text]
#         for sc in subchunks:
#             all_text_chunks.append(sc.strip())
#             # merge provided metadata + auto metadata + upload metadata
#             row_meta = {**metadata, **d.get("metadata", {})}
#             all_metas.append(row_meta)

#     # dedupe but keep first seen meta for each unique text
#     seen = {}
#     unique_texts = []
#     unique_metas = []
#     for txt, m in zip(all_text_chunks, all_metas):
#         if txt not in seen:
#             seen[txt] = True
#             unique_texts.append(txt)
#             unique_metas.append(m)

#     if not unique_texts:
#         return {"status": "empty", "count": 0}

#     # sanitize metas to acceptable chroma types (str,int,float,bool,None)
#     for meta in unique_metas:
#         for k, v in list(meta.items()):
#             if isinstance(v, list):
#                 meta[k] = ", ".join(map(str, v))
#             elif not isinstance(v, (str, int, float, bool)) and v is not None:
#                 meta[k] = str(v)

#     embeddings = embedder.encode(unique_texts, convert_to_numpy=True, show_progress_bar=False)
#     ids = [f"{filename}_{i}" for i in range(len(unique_texts))]

#     collection.upsert(
#         ids=ids,
#         embeddings=embeddings.tolist(),
#         documents=unique_texts,
#         metadatas=unique_metas,
#     )

#     return {"status": "ok", "count": len(unique_texts)}

# def ingest_folder(folder_path: str) -> Dict:
#     allowed_exts = [".pdf", ".docx", ".doc", ".csv", ".xlsx", ".xls", ".txt", ".md"]
#     summary = {"total_chunks": 0, "files": []}
#     for f in Path(folder_path).rglob("*"):
#         if f.suffix.lower() in allowed_exts:
#             with open(f, "rb") as fh:
#                 res = ingest_file_bytes(fh.read(), f.name, metadata={"path": str(f)})
#             summary["files"].append({f.name: res})
#             summary["total_chunks"] += res.get("count", 0)
#     print(f"✅ Ingested {summary['total_chunks']} chunks from {len(summary['files'])} files.")
#     return summary

# if __name__ == "__main__":
#     import argparse, json
#     parser = argparse.ArgumentParser()
#     parser.add_argument("--folder", help="Folder to ingest", required=True)
#     args = parser.parse_args()
#     out = ingest_folder(args.folder)
#     print(json.dumps(out, indent=2))


# # ingest.py befoe re last edit-------------------------------------
import os
from pathlib import Path
from typing import Dict, List, Optional
import pandas as pd
import re
from sentence_transformers import SentenceTransformer
import chromadb
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Directories
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
CHROMA_DIR = os.path.join(BASE_DIR, "db", "chroma")
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(CHROMA_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "all-MiniLM-L6-v2")

# Tunable parameters
CHUNK_SIZE = int(os.environ.get("CHUNK_SIZE", 1500))
CHUNK_OVERLAP = int(os.environ.get("CHUNK_OVERLAP", 300))
TOP_K = int(os.environ.get("RETRIEVE_TOP_K", 20))

print("📂 Using CHROMA_DIR:", CHROMA_DIR)
print("📂 Using DATA_DIR:", DATA_DIR)

# Initialize
embedder = SentenceTransformer(EMBEDDING_MODEL)
client = chromadb.PersistentClient(path=CHROMA_DIR)
collection = client.get_or_create_collection("DepartmentLLM")

def clean_text(text: str) -> str:
    if not text:
        return ""
    text = str(text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()

EVENT_KEYWORDS = ["event", "workshop", "seminar", "guest lecture", "hackathon"]
PAPER_KEYWORDS = ["paper", "publication", "conference", "journal"]
TIMETABLE_KEYWORDS = ["timetable", "time table", "schedule"]
JOURNAL_KEYWORDS = ["journal"]
RESEARCH_KEYWORDS = ["research", "project"]

# def infer_doc_type(text: str) -> str:
#     t = text.lower()
#     if any(k in t for k in EVENT_KEYWORDS):
#         return "event"
#     if any(k in t for k in PAPER_KEYWORDS):
#         return "paper"
#     if any(k in t for k in JOURNAL_KEYWORDS):
#         return "journal"
#     if any(k in t for k in TIMETABLE_KEYWORDS):
#         return "timetable"
#     if any(k in t for k in RESEARCH_KEYWORDS):
#         return "research"
#     return "general"

def infer_doc_type(row_text: str) -> str:
    text = row_text.lower()

    if "conference" in text or "ieee" in text or "isbn" in text:
        return "conference_paper"

    if "journal" in text or "issn" in text:
        return "journal_paper"

    if "guest lecture" in text or "visit" in text or "workshop" in text:
        return "event"

    return "other"

# def extract_metadata_from_row(row: pd.Series) -> Dict:
#     """Auto-extract useful metadata like year, coordinators, speakers."""
#     text = " ".join([str(x) for x in row.values if pd.notna(x)])
#     meta = {}
#     if match := re.search(r"(20\d{2})", text):
#         meta["year"] = match.group(1)
#     if match := re.search(r"Coordinator[s]?:\s*([A-Za-z0-9.,&\s()-]+)", text, re.I):
#         meta["coordinators"] = ", ".join([c.strip() for c in match.group(1).split(",")])
#     if match := re.search(r"Speaker[s]?:\s*([A-Za-z0-9.,&\s()-]+)", text, re.I):
#         meta["speakers"] = ", ".join([c.strip() for c in match.group(1).split(",")])
#     return meta

# def extract_metadata(text: str) -> dict:
#     meta = {}

#     # Year
#     if m := re.search(r"(19|20)\d{2}", text):
#         meta["year"] = m.group(0)

#     # # Event name
#     # if m := re.search(r"(?i)(?:conference|event)\s*[:\-]?\s*(.*)", text):
#     #     meta["event_name"] = m.group(1).strip()

#     # # Author / Coordinator
#     # # Assuming the first name/title is coordinator
#     # if m := re.search(r"\d*\s*(Dr\.|Mrs\.|Mr\.)\s*([A-Za-z\s]+)", text):
#     #     meta["coordinators"] = m.group(0).strip()  # full match includes title + name

#     # # Authors (if separate field exists)
#     # if m := re.search(r"Author[s]?:\s*(.*)", text, re.I):
#     #     meta["authors"] = m.group(1).strip()

#     # meta["doc_type"] = infer_doc_type(text)

#     # store raw text for later logic
#     meta["raw_text"] = text.lower()
#     return meta

def extract_metadata_from_row(row: pd.Series) -> Dict:
    meta = {}

    # Join row text (robust across any Excel format)
    values = [str(v) for v in row.values if pd.notna(v)]
    joined_text = " | ".join(values)
    t = joined_text.lower()

    # -------- YEAR --------
    if m := re.search(r"(19|20)\d{2}", joined_text):
        meta["year"] = m.group(0)

    # -------- PERSON (AUTHOR / FACULTY / COORDINATOR) --------
    # Works even if column names change
    if m := re.search(r"(dr\.|mrs\.|mr\.)\s*[a-z.\s]+", t):
        meta["person"] = m.group(0).title().strip()

    # -------- DOCUMENT TYPE --------
    if "conference" in t or "ieee" in t or "isbn" in t:
        meta["doc_type"] = "conference_paper"
    elif "journal" in t or "issn" in t or "wiley" in t or "springer" in t:
        meta["doc_type"] = "journal_paper"
    elif any(k in t for k in ["workshop", "seminar", "guest lecture", "visit", "fdp"]):
        meta["doc_type"] = "event"
    else:
        meta["doc_type"] = "other"

    # -------- RAW TEXT (IMPORTANT) --------
    meta["raw_text"] = t

    return meta


# def dataframe_to_chunks(df: pd.DataFrame, sheet_name: str) -> List[Dict]:
#     if df.empty:
#         return []

#     chunks = []

#     for _, row in df.iterrows():
#         text = " ".join(str(x) for x in row.values if pd.notna(x))
#         cleaned_text = clean_text(text)

#         doc_type = infer_doc_type(cleaned_text)

#         chunks.append({
#             "text": cleaned_text,
#             "metadata": {
#                 **extract_metadata(cleaned_text),
#                 "sheet": sheet_name,
#                 "doc_type": doc_type
#             }
#         })

#     return chunks

def dataframe_to_chunks(df: pd.DataFrame, sheet_name: str) -> List[Dict]:
    chunks = []

    for _, row in df.iterrows():
        text = " | ".join(str(v) for v in row.values if pd.notna(v))
        meta = extract_metadata_from_row(row)

        meta["sheet"] = sheet_name
        meta["raw_text"] = text.lower()

        chunks.append({
            "text": clean_text(text),
            "metadata": meta
        })

    return chunks



# def dataframe_to_chunks(df: pd.DataFrame) -> List[Dict]:
#     if df.empty:
#         return []
#     chunks = []
#     for _, row in df.iterrows():
#         # text = ", ".join([f"{c}: {row[c]}" for c in df.columns if pd.notna(row[c])])
#         # chunks.append({"text": clean_text(text), "metadata": extract_metadata(row)})
#         text = " ".join([str(x) for x in row.values if pd.notna(x)])
#         cleaned_text = clean_text(text)
#         meta = extract_metadata(cleaned_text)
#         chunks.append({"text": cleaned_text, "metadata": {
#         **extract_metadata(cleaned_text),
#         "sheet": sheet_name
#     }})
#     return chunks

def extract_text_from_file(file_bytes: bytes, filename: str) -> List[Dict]:
    ext = Path(filename).suffix.lower()
    temp_path = f"./tmp_{filename}"
    with open(temp_path, "wb") as f:
        f.write(file_bytes)
    docs = []
    try:
        if ext == ".csv":
            df = pd.read_csv(temp_path)
            docs = dataframe_to_chunks(df,sheet_name="CSV")
        elif ext in [".xlsx", ".xls"]:
            xls = pd.read_excel(temp_path, sheet_name=None)
            for sheet_name, df in xls.items():
                # for c in dataframe_to_chunks(df):
                #     c["metadata"]["sheet"] = sheet_name
                #     docs.append(c)
                docs.extend(dataframe_to_chunks(df, sheet_name))

        else:
            text = open(temp_path, encoding="utf-8", errors="ignore").read()
            docs = [{"text": clean_text(text), "metadata": extract_metadata_from_row(text)}]
            #docs = [{"text": clean_text(text), "metadata": {}}]
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
    return docs

def ingest_file_bytes(file_bytes: bytes, filename: str, metadata: Optional[Dict] = None) -> Dict:
    metadata = metadata or {}
    docs = extract_text_from_file(file_bytes, filename)
    if not docs:
        return {"status": "empty", "count": 0}

    splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
    texts, metas = [], []

    for d in docs:
        chunks = splitter.split_text(d["text"]) if len(d["text"]) > 400 else [d["text"]]
        for c in chunks:
            texts.append(c)
            metas.append({**metadata, **d.get("metadata", {})})

    # Deduplicate
    seen, uniq_texts, uniq_metas = set(), [], []
    for t, m in zip(texts, metas):
        if t not in seen:
            seen.add(t)
            uniq_texts.append(t)
            uniq_metas.append(m)

    if not uniq_texts:
        return {"status": "empty", "count": 0}

    embeddings = embedder.encode(uniq_texts, convert_to_numpy=True, show_progress_bar=False)
    ids = [f"{filename}_{i}" for i in range(len(uniq_texts))]
    collection.upsert(ids=ids, embeddings=embeddings.tolist(), documents=uniq_texts, metadatas=uniq_metas)
    return {"status": "ok", "count": len(uniq_texts)}

def ingest_folder(folder_path: str) -> Dict:
    allowed_exts = [".pdf", ".csv", ".xlsx", ".xls", ".txt", ".docx"]
    summary = {"total_chunks": 0, "files": []}
    for f in Path(folder_path).rglob("*"):
        if f.suffix.lower() in allowed_exts:
            with open(f, "rb") as fh:
                res = ingest_file_bytes(fh.read(), f.name, metadata={"path": str(f)})
            summary["files"].append({f.name: res})
            summary["total_chunks"] += res.get("count", 0)
    print(f"✅ Ingested {summary['total_chunks']} chunks from {len(summary['files'])} files.")
    return summary

if __name__ == "__main__":
    import argparse, json
    parser = argparse.ArgumentParser()
    parser.add_argument("--folder", required=True)
    args = parser.parse_args()
    out = ingest_folder(args.folder)
    print(json.dumps(out, indent=2))
 

# ## # # ingest.py 13-11-25
# # ingest.py
# import os
# from pathlib import Path
# from typing import Dict, List, Optional
# import pandas as pd
# import re
# from sentence_transformers import SentenceTransformer
# import chromadb
# from langchain_text_splitters import RecursiveCharacterTextSplitter

# # =============================
# # Directories
# # =============================
# BASE_DIR = os.path.dirname(os.path.dirname(__file__))
# CHROMA_DIR = os.path.join(BASE_DIR, "db", "chroma")
# DATA_DIR = os.path.join(BASE_DIR, "data")
# os.makedirs(CHROMA_DIR, exist_ok=True)
# os.makedirs(DATA_DIR, exist_ok=True)

# EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "all-MiniLM-L6-v2")

# # Tunable parameters
# CHUNK_SIZE = int(os.environ.get("CHUNK_SIZE", 1500))
# CHUNK_OVERLAP = int(os.environ.get("CHUNK_OVERLAP", 300))
# TOP_K = int(os.environ.get("RETRIEVE_TOP_K", 20))

# print("📂 Using CHROMA_DIR:", CHROMA_DIR)
# print("📂 Using DATA_DIR:", DATA_DIR)

# # =============================
# # Initialize
# # =============================
# embedder = SentenceTransformer(EMBEDDING_MODEL)
# client = chromadb.PersistentClient(path=CHROMA_DIR)
# collection = client.get_or_create_collection("DepartmentLLM")


# # =============================
# # Helper: Text cleaning
# # =============================
# def clean_text(text: str) -> str:
#     if not text:
#         return ""
#     text = str(text)
#     # Remove Unnamed columns, multiple spaces, extra punctuation
#     text = re.sub(r"Unnamed[:\d]*", "", text)
#     text = re.sub(r"[\t\n\r]+", " ", text)
#     text = re.sub(r"\s+", " ", text)
#     text = text.strip(" ,.-")
#     return text.strip()


# # =============================
# # Helper: Extract structured metadata
# # =============================
# def extract_metadata_from_row(row: pd.Series) -> Dict:
#     text = " ".join([str(x) for x in row.values if pd.notna(x)])
#     meta = {}

#     # Extract year
#     if match := re.search(r"\b(20\d{2})\b", text):
#         meta["year"] = match.group(1)

#     # Extract coordinator(s)
#     if match := re.search(r"Coordinator[s]?:\s*([A-Za-z0-9.,/&\s()-]+)", text, re.I):
#         meta["coordinators"] = ", ".join([c.strip() for c in match.group(1).split(",")])

#     # Extract speaker(s)
#     if match := re.search(r"Speaker[s]?:\s*([A-Za-z0-9.,/&\s()-]+)", text, re.I):
#         meta["speakers"] = ", ".join([c.strip() for c in match.group(1).split(",")])

#     # Extract event name keywords
#     if match := re.search(r"(Event|Workshop|Hackathon|Expo|Seminar|Conference|Competition)[:\s-]*([A-Za-z0-9.,/&\s()-]+)", text, re.I):
#         meta["event_name"] = match.group(2).strip()

#     return meta


# # =============================
# # Convert DataFrame rows → text chunks
# # =============================
# def dataframe_to_chunks(df: pd.DataFrame) -> List[Dict]:
#     if df.empty:
#         return []
#     chunks = []
#     for _, row in df.iterrows():
#         # Combine column headers and values for meaningful text
#         text_parts = []
#         for col in df.columns:
#             if pd.notna(row[col]):
#                 text_parts.append(f"{col}: {row[col]}")
#         text = ", ".join(text_parts)
#         cleaned = clean_text(text)
#         chunks.append({"text": cleaned, "metadata": extract_metadata_from_row(row)})
#     return chunks


# # =============================
# # Extract from different file types
# # =============================
# def extract_text_from_file(file_bytes: bytes, filename: str) -> List[Dict]:
#     ext = Path(filename).suffix.lower()
#     temp_path = f"./tmp_{filename}"
#     with open(temp_path, "wb") as f:
#         f.write(file_bytes)

#     docs = []
#     try:
#         if ext == ".csv":
#             df = pd.read_csv(temp_path)
#             docs = dataframe_to_chunks(df)
#         elif ext in [".xlsx", ".xls"]:
#             xls = pd.read_excel(temp_path, sheet_name=None)
#             for sheet_name, df in xls.items():
#                 for c in dataframe_to_chunks(df):
#                     c["metadata"]["sheet"] = sheet_name
#                     docs.append(c)
#         else:
#             text = open(temp_path, encoding="utf-8", errors="ignore").read()
#             docs = [{"text": clean_text(text), "metadata": {}}]
#     finally:
#         if os.path.exists(temp_path):
#             os.remove(temp_path)

#     return docs


# # =============================
# # Ingest single file
# # =============================
# def ingest_file_bytes(file_bytes: bytes, filename: str, metadata: Optional[Dict] = None) -> Dict:
#     metadata = metadata or {}
#     docs = extract_text_from_file(file_bytes, filename)
#     if not docs:
#         return {"status": "empty", "count": 0}

#     splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
#     texts, metas = [], []

#     for d in docs:
#         chunks = splitter.split_text(d["text"]) if len(d["text"]) > 400 else [d["text"]]
#         for c in chunks:
#             texts.append(c)
#             metas.append({**metadata, **d.get("metadata", {})})

#     # Deduplicate text
#     seen, uniq_texts, uniq_metas = set(), [], []
#     for t, m in zip(texts, metas):
#         if t not in seen and len(t.strip()) > 10:
#             seen.add(t)
#             uniq_texts.append(t)
#             uniq_metas.append(m)

#     if not uniq_texts:
#         return {"status": "empty", "count": 0}

#     # Generate embeddings
#     embeddings = embedder.encode(uniq_texts, convert_to_numpy=True, show_progress_bar=True)
#     ids = [f"{filename}_{i}" for i in range(len(uniq_texts))]

#     collection.upsert(ids=ids, embeddings=embeddings.tolist(), documents=uniq_texts, metadatas=uniq_metas)
#     print(f"📘 Added {len(uniq_texts)} chunks from {filename}")
#     return {"status": "ok", "count": len(uniq_texts)}


# # =============================
# # Ingest entire folder
# # =============================
# def ingest_folder(folder_path: str) -> Dict:
#     allowed_exts = [".pdf", ".csv", ".xlsx", ".xls", ".txt", ".docx"]
#     summary = {"total_chunks": 0, "files": []}

#     for f in Path(folder_path).rglob("*"):
#         if f.suffix.lower() in allowed_exts:
#             with open(f, "rb") as fh:
#                 res = ingest_file_bytes(fh.read(), f.name, metadata={"path": str(f)})
#             summary["files"].append({f.name: res})
#             summary["total_chunks"] += res.get("count", 0)

#     print(f"✅ Ingested {summary['total_chunks']} chunks from {len(summary['files'])} files.")
#     return summary


# # =============================
# # CLI entry point
# # =============================
# if __name__ == "__main__":
#     import argparse, json
#     parser = argparse.ArgumentParser()
#     parser.add_argument("--folder", required=True)
#     args = parser.parse_args()
#     out = ingest_folder(args.folder)
#     print(json.dumps(out, indent=2))
