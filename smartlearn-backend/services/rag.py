# ============================================================
# rag.py - RAG pipeline helpers: pages -> chunks -> embeddings
# ============================================================
# Day 3 builds reusable RAG logic here. The small-PDF Day 2 path
# (pdf.py + llm.py) is untouched; this module is the long-PDF path.
# Notebooks and the backend upload/chat routes both call these helpers.

import json
import os
import re
from io import BytesIO
from pathlib import Path

import numpy as np
from pypdf import PdfReader

# ---------------------------------------------------------------------------
# Text cleaning and page loading
# ---------------------------------------------------------------------------


def clean_text(text: str) -> str:
    """Normalize one extracted page of PDF text.

    Removes null bytes and soft hyphens, collapses repeated whitespace, and
    trims noisy line breaks so chunk boundaries are meaningful.
    """
    text = text.replace("\x00", "")                # null bytes from some PDFs
    text = text.replace("­", "")              # soft hyphens (in-word line breaks)
    text = re.sub(r"[ \t]+", " ", text)            # collapse spaces/tabs
    text = re.sub(r" *\n *", "\n", text)           # trim spaces around newlines
    text = re.sub(r"\n{3,}", "\n\n", text)         # collapse blank-line runs
    return text.strip()


def extract_pages_from_bytes_for_rag(pdf_bytes: bytes) -> list[dict]:
    """Read uploaded PDF bytes into ``[{"page": N, "text": "..."}]``.

    Preserves original PDF page numbers and drops empty text blocks.
    No page-count cap -- RAG handles long PDFs (unlike the Day 2 small path).
    """
    reader = PdfReader(BytesIO(pdf_bytes))
    pages = []
    for number, page in enumerate(reader.pages, start=1):
        text = clean_text(page.extract_text() or "")
        if text:
            pages.append({"page": number, "text": text})
    return pages


def extract_pages_for_rag(file_path, page_limit: int | None = None) -> list[dict]:
    """Read a local PDF path into page records (for notebook tests)."""
    reader = PdfReader(str(file_path))
    pages = []
    for number, page in enumerate(reader.pages, start=1):
        if page_limit is not None and number > page_limit:
            break
        text = clean_text(page.extract_text() or "")
        if text:
            pages.append({"page": number, "text": text})
    return pages


# ---------------------------------------------------------------------------
# JSON artifact I/O
# ---------------------------------------------------------------------------


def save_json(obj, path):
    """Save one Python object to a UTF-8 JSON file, creating parents."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(obj, handle, ensure_ascii=False, indent=2)
    return path


def load_json(path):
    """Read a saved JSON artifact back into a Python object."""
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


# ---------------------------------------------------------------------------
# Chunking: paragraph | character | character_overlap
# ---------------------------------------------------------------------------


def slice_long_text(text: str, chunk_size: int) -> list[str]:
    """Split one oversized text block, preferring word boundaries."""
    words = text.split(" ")
    pieces, current, current_len = [], [], 0
    for word in words:
        if current and current_len + len(word) + 1 > chunk_size:
            pieces.append(" ".join(current))
            current, current_len = [], 0
        current.append(word)
        current_len += len(word) + 1
    if current:
        pieces.append(" ".join(current))
    return [piece for piece in pieces if piece.strip()]


def chunk_by_paragraph(records: list[dict], chunk_size: int = 700) -> list[dict]:
    """Paragraph mode: keep paragraph boundaries; split oversized paragraphs."""
    chunks, chunk_id = [], 0
    for record in records:
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", record["text"]) if p.strip()]
        for para in paragraphs:
            if len(para) <= chunk_size:
                chunk_id += 1
                chunks.append({
                    "chunk_id": f"chunk-{chunk_id:04d}",
                    "page": record["page"],
                    "text": para,
                    "chunk_mode": "paragraph",
                })
            else:
                for piece in slice_long_text(para, chunk_size):
                    chunk_id += 1
                    chunks.append({
                        "chunk_id": f"chunk-{chunk_id:04d}",
                        "page": record["page"],
                        "text": piece,
                        "chunk_mode": "paragraph",
                    })
    return chunks


def chunk_by_characters(records: list[dict], chunk_size: int = 700, overlap: int = 0) -> list[dict]:
    """Fixed-size sliding-window chunks, with optional overlap.

    ``overlap > 0`` moves the next window start to ``chunk_size - overlap`` so
    evidence spanning a boundary appears in at least one chunk.
    """
    chunks, chunk_id = [], 0
    step = max(1, chunk_size - overlap)
    mode = "character" if overlap == 0 else "character_overlap"
    for record in records:
        text = record["text"]
        start = 0
        while start < len(text):
            piece = text[start:start + chunk_size].strip()
            if piece:
                chunk_id += 1
                chunks.append({
                    "chunk_id": f"chunk-{chunk_id:04d}",
                    "page": record["page"],
                    "text": piece,
                    "chunk_mode": mode,
                })
            if start + chunk_size >= len(text):
                break
            start += step
    return chunks


def build_chunks(records: list[dict], chunk_mode: str = "character_overlap",
                 chunk_size: int = 700, overlap: int = 120) -> list[dict]:
    """Select the requested chunking strategy.

    ``chunk_mode`` supports exactly: ``"paragraph"``, ``"character"``,
    ``"character_overlap"``. Every chunk keeps the same schema:
    ``{chunk_id, page, text, chunk_mode}``.
    """
    if chunk_mode == "paragraph":
        return chunk_by_paragraph(records, chunk_size)
    if chunk_mode == "character":
        return chunk_by_characters(records, chunk_size, overlap=0)
    if chunk_mode == "character_overlap":
        return chunk_by_characters(records, chunk_size, overlap=overlap)
    raise ValueError(f"Unknown chunk_mode: {chunk_mode!r}")


# ---------------------------------------------------------------------------
# Embeddings
# ---------------------------------------------------------------------------

_MODEL_CACHE: dict = {}


def model_tag(model_name: str) -> str:
    """Turn a model name into a safe filename suffix."""
    return re.sub(r"[/\-\.]", "_", model_name).strip("_")


def get_device() -> str:
    """Return ``"cuda"`` when a GPU is available, otherwise ``"cpu"``."""
    try:
        import torch
        return "cuda" if torch.cuda.is_available() else "cpu"
    except ImportError:
        return "cpu"


def resolve_model_source(model_name: str, model_cache_dir=None) -> str:
    """Prefer a local cached model folder; fall back to the model name.

    Hugging Face is unreachable in this environment, so the MiniLM model is
    downloaded once from ModelScope into a local folder. Check known local
    locations before ever asking sentence-transformers to fetch remotely.
    """
    candidates = []
    if model_cache_dir:
        candidates.append(Path(model_cache_dir))
    # Backend default cache: smartlearn-backend/artifacts/rag/hf_models/<basename>.
    # ModelScope snapshots use the model basename (all-MiniLM-L6-v2), not the
    # "org/model" full name, so compare on the basename.
    basename = model_name.rsplit("/", 1)[-1]
    candidates.append(Path(__file__).resolve().parent.parent / "artifacts" / "rag" / "hf_models" / basename)
    for candidate in candidates:
        if (candidate / "modules.json").exists():
            return str(candidate)
    return model_name


def load_model(model_name: str, device: str | None = None, model_cache_dir=None):
    """Create or reuse one SentenceTransformer instance (CPU-first)."""
    source = resolve_model_source(model_name, model_cache_dir=model_cache_dir)
    key = f"{source}::{device or 'auto'}"
    if key not in _MODEL_CACHE:
        from sentence_transformers import SentenceTransformer
        dev = device or get_device()
        try:
            _MODEL_CACHE[key] = SentenceTransformer(
                source, device=dev, model_kwargs={"use_safetensors": False}
            )
        except Exception:
            # No pytorch_model.bin in the snapshot -- let the loader auto-detect.
            _MODEL_CACHE[key] = SentenceTransformer(source, device=dev)
    return _MODEL_CACHE[key]


def embed_texts(texts, model_name: str, model_cache_dir=None, batch_size: int = 32) -> np.ndarray:
    """Encode a list of texts into normalized float32 embeddings."""
    model = load_model(model_name, model_cache_dir=model_cache_dir)
    vectors = model.encode(
        list(texts),
        batch_size=batch_size,
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    return np.asarray(vectors, dtype=np.float32)


# ---------------------------------------------------------------------------
# Artifact paths and the pages -> chunks -> embeddings -> manifest bundle
# ---------------------------------------------------------------------------


def artifact_paths_for(document_id: str, pdf_name: str, chunk_mode: str,
                       model_name: str, chunk_size: int, overlap: int,
                       artifact_root=None) -> dict:
    """Decide where pages, chunks, embeddings, manifest and index are saved."""
    root = Path(artifact_root) if artifact_root else Path(__file__).resolve().parent.parent / "artifacts" / "rag"
    tag = model_tag(model_name)
    return {
        "raw_pages": root / "raw_pages" / f"{document_id}_pages.json",
        "chunks": root / "chunks" / f"{document_id}_{chunk_mode}.json",
        "embeddings": root / "embeddings" / f"{document_id}_{chunk_mode}_{tag}.npy",
        "manifest": root / "embeddings" / f"{document_id}_{chunk_mode}_{tag}.manifest.json",
        "index_dir": root / document_id / f"{chunk_mode}_c{chunk_size}_o{overlap}_{tag}",
    }


def ensure_artifacts(document_id: str, pdf_name: str, pages: list[dict],
                     chunk_mode: str = "character_overlap",
                     model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
                     chunk_size: int = 700, overlap: int = 120,
                     batch_size: int = 32, artifact_root=None) -> dict:
    """Build or reuse the full pages -> chunks -> embeddings -> manifest bundle.

    Returns ``{"chunks": [...], "embeddings": np.ndarray, "manifest": {...},
    "paths": {...}}``. Reuses saved outputs only when the signature matches.
    """
    paths = artifact_paths_for(document_id, pdf_name, chunk_mode, model_name,
                               chunk_size, overlap, artifact_root)

    if paths["manifest"].exists() and paths["chunks"].exists() and paths["embeddings"].exists():
        manifest = load_json(paths["manifest"])
        signature_matches = (
            manifest.get("document_id") == document_id
            and manifest.get("pdf_name") == pdf_name
            and manifest.get("chunk_mode") == chunk_mode
            and manifest.get("chunk_size") == chunk_size
            and manifest.get("overlap") == overlap
            and manifest.get("model_name") == model_name
            and manifest.get("num_pages") == len(pages)
        )
        if signature_matches:
            return {
                "chunks": load_json(paths["chunks"]),
                "embeddings": np.load(paths["embeddings"], allow_pickle=False),
                "manifest": manifest,
                "paths": paths,
            }

    save_json(pages, paths["raw_pages"])
    chunks = build_chunks(pages, chunk_mode=chunk_mode, chunk_size=chunk_size, overlap=overlap)
    save_json(chunks, paths["chunks"])

    embeddings = embed_texts(
        [chunk["text"] for chunk in chunks],
        model_name,
        batch_size=batch_size,
    )
    paths["embeddings"].parent.mkdir(parents=True, exist_ok=True)
    np.save(paths["embeddings"], embeddings)

    manifest = {
        "document_id": document_id,
        "pdf_name": pdf_name,
        "num_pages": len(pages),
        "chunk_mode": chunk_mode,
        "chunk_size": chunk_size,
        "overlap": overlap,
        "model_name": model_name,
        "num_chunks": len(chunks),
        "embedding_dim": int(embeddings.shape[1]),
        "device": get_device(),
        "chunk_path": str(paths["chunks"]),
        "embedding_path": str(paths["embeddings"]),
        "raw_pages_path": str(paths["raw_pages"]),
    }
    save_json(manifest, paths["manifest"])

    return {"chunks": chunks, "embeddings": embeddings, "manifest": manifest, "paths": paths}


# ---------------------------------------------------------------------------
# Path display helper (used by notebook verification cells)
# ---------------------------------------------------------------------------


def relative_path_str(path, base) -> str:
    """Return ``path`` relative to ``base`` when possible, else the raw path."""
    try:
        return str(Path(path).resolve().relative_to(Path(base).resolve()))
    except ValueError:
        return str(path)


# ---------------------------------------------------------------------------
# FAISS index helpers
# ---------------------------------------------------------------------------


def build_faiss_index(embeddings: np.ndarray):
    """Build a FAISS inner-product index over normalized embeddings."""
    import faiss
    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(np.ascontiguousarray(embeddings, dtype=np.float32))
    return index


def save_faiss_index(index, index_path):
    import faiss
    index_path = Path(index_path)
    index_path.parent.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(index_path))
    return index_path


def load_faiss_index(index_path):
    import faiss
    return faiss.read_index(str(index_path))


def ensure_index(document_id: str, pdf_name: str, pages: list[dict] | None = None,
                 pdf_path=None, chunk_mode: str = "character_overlap",
                 model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
                 chunk_size: int = 700, overlap: int = 120, batch_size: int = 32,
                 artifact_root=None) -> dict:
    """Build or reuse a FAISS index for one document.

    Returns the ensure_artifacts bundle plus ``index`` and ``index_path``.
    The index is rebuilt only when the artifact signature changes.
    """
    if pages is None:
        pages = extract_pages_for_rag(pdf_path)

    bundle = ensure_artifacts(document_id, pdf_name, pages, chunk_mode, model_name,
                              chunk_size, overlap, batch_size, artifact_root)
    paths = bundle["paths"]
    index_path = paths["index_dir"] / "index.faiss"
    meta_path = paths["index_dir"] / "index.meta.json"
    manifest = bundle["manifest"]

    signature = {
        "document_id": document_id,
        "pdf_name": pdf_name,
        "chunk_mode": chunk_mode,
        "chunk_size": chunk_size,
        "overlap": overlap,
        "model_name": model_name,
        "num_chunks": len(bundle["chunks"]),
        "embedding_dim": int(bundle["embeddings"].shape[1]),
    }

    if index_path.exists() and meta_path.exists() and load_json(meta_path) == signature:
        bundle["index"] = load_faiss_index(index_path)
    else:
        index = build_faiss_index(bundle["embeddings"])
        save_faiss_index(index, index_path)
        save_json(signature, meta_path)
        bundle["index"] = index

    bundle["index_path"] = index_path
    bundle["paths"]["index"] = index_path
    return bundle


def prepare_rag_document(document_id: str, filename: str, pages: list[dict],
                         chunk_mode: str = "character_overlap",
                         chunk_size: int = 700, overlap: int = 120,
                         model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
                         batch_size: int = 32, artifact_root=None) -> dict:
    """Prepare one server-style document record with retrieval assets."""
    bundle = ensure_index(document_id, filename, pages=pages, chunk_mode=chunk_mode,
                          model_name=model_name, chunk_size=chunk_size, overlap=overlap,
                          batch_size=batch_size, artifact_root=artifact_root)
    return {
        "document_id": document_id,
        "filename": filename,
        "pages": pages,
        "chunks": bundle["chunks"],
        "chunk_size": len(bundle["chunks"]),          # notebook reads this as chunk count
        "embedding_dim": bundle["manifest"]["embedding_dim"],
        "model_name": model_name,
        "model_source": resolve_model_source(model_name),
        "artifacts": {
            "index": bundle["index_path"],
            "chunks": bundle["paths"]["chunks"],
            "embeddings": bundle["paths"]["embeddings"],
            "manifest": bundle["paths"]["manifest"],
        },
        "history": [],
    }


# ---------------------------------------------------------------------------
# Retrieval: search hits -> local answer / LLM answer -> citations + sources
# ---------------------------------------------------------------------------


def keyword_set(text: str) -> set:
    """Lightweight lexical tokens for simple reranking."""
    return set(re.findall(r"[a-z0-9]+", (text or "").lower()))


def search_bundle(question: str, bundle: dict, top_k: int = 3, candidate_pool: int = 60,
                  batch_size: int = 1, history: list[dict] | None = None) -> list[dict]:
    """Embed the question, search the index, and return top-k hits."""
    query = embed_texts([question], bundle["model_name"],
                        model_cache_dir=bundle.get("model_source"), batch_size=batch_size)
    index = bundle["index"]
    scores, ids = index.search(query, candidate_pool)

    hits = []
    for score, idx in zip(scores[0], ids[0]):
        if idx < 0 or idx >= len(bundle["chunks"]):
            continue
        chunk = bundle["chunks"][int(idx)]
        hits.append({
            "page": chunk["page"],
            "chunk_id": chunk["chunk_id"],
            "text": chunk["text"],
            "score": float(score),
        })

    # Light lexical rerank: prefer chunks sharing keywords with the question.
    q_tokens = keyword_set(question)
    if q_tokens:
        hits.sort(
            key=lambda h: (len(q_tokens & keyword_set(h["text"])), h["score"]),
            reverse=True,
        )
    return hits[:top_k]


def search_document(question: str, document: dict, top_k: int = 3, candidate_pool: int = 60,
                    history: list[dict] | None = None) -> list[dict]:
    """Load a prepared document's index and return top-k hits."""
    bundle = {
        "index": load_faiss_index(document["artifacts"]["index"]),
        "chunks": document["chunks"],
        "model_name": document["model_name"],
        "model_source": document.get("model_source"),
    }
    return search_bundle(question, bundle, top_k=top_k, candidate_pool=candidate_pool,
                         history=history)


def split_sentences(text: str) -> list[str]:
    return [part.strip() for part in re.split(r"(?<=[.!?])\s+", text or "") if part.strip()]


def best_sentence_answer(question: str, hits: list[dict]) -> str:
    """Pick the best answer sentence from retrieved hits, with a page tag."""
    if not hits:
        return "No relevant evidence was found in the document."
    q_tokens = keyword_set(question)
    best, best_score = "", -1.0
    for hit in hits:
        for sentence in split_sentences(hit["text"]):
            tokens = keyword_set(sentence)
            score = len(q_tokens & tokens) + hit["score"] * 0.01
            if score > best_score:
                best, best_score = sentence, score
    if not best:
        return "No answer found in the retrieved evidence."
    return f"{best} [Page {hits[0]['page']}]"


SYSTEM_PROMPT = (
    "You answer messages only from the supplied PDF text. "
    "Cite factual claims with [Page X]. "
    "If the answer is not in the PDF, say that the document does not provide enough information. "
    "Never invent a page number."
)


def build_grounded_user_prompt(question: str, hits: list[dict],
                               history: list[dict] | None = None) -> str:
    """Build one grounded prompt from retrieved chunks plus recent history."""
    evidence = "\n\n".join(
        f"### [Page {hit['page']}] ({hit['chunk_id']})\n{hit['text']}"
        for hit in hits
    )
    history_block = ""
    if history:
        history_block = "\n\nRecent conversation:\n" + "\n".join(
            f"user: {turn.get('question', '')}\nassistant: {turn.get('answer', '')}"
            for turn in history[-4:]
        )
    return f"PDF text:\n{evidence}\n{history_block}\n\nmessage: {question}"


def _llm_client():
    """Return (OpenAI client, model) for DeepSeek or OpenRouter, or None."""
    import os
    from openai import OpenAI
    api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        return None
    if os.getenv("OPENROUTER_API_KEY"):
        return OpenAI(api_key=api_key, base_url="https://openrouter.ai/api/v1"), \
            os.getenv("OPENROUTER_MODEL", "openrouter/free")
    return OpenAI(api_key=api_key, base_url="https://api.deepseek.com/v1"), \
        os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash")


def _llm_answer_from_hits(question: str, hits: list[dict],
                          history: list[dict] | None = None,
                          answer_model: str = "openrouter/free") -> str | None:
    """Answer from retrieved hits via the LLM; None when no key is configured."""
    client_info = _llm_client()
    if client_info is None:
        return None
    client, model = client_info
    response = client.chat.completions.create(
        model=model,
        temperature=0.0,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_grounded_user_prompt(question, hits, history)},
        ],
    )
    return response.choices[0].message.content or ""


def extract_citations(answer: str, hits: list[dict] | None = None) -> list[int]:
    """Page numbers cited in the answer, restricted to pages present in hits."""
    known = {hit["page"] for hit in hits} if hits else None
    cited = {int(number) for number in re.findall(r"\[Page\s+(\d+)\]", answer or "")}
    if known is not None:
        cited = {number for number in cited if number in known}
    return sorted(cited)


def build_sources(hits: list[dict]) -> list[dict]:
    return [
        {"page": hit["page"], "chunk_id": hit["chunk_id"],
         "score": hit["score"], "preview": hit["text"][:200]}
        for hit in hits
    ]


def answer_document(document: dict, question: str, top_k: int = 3, candidate_pool: int = 60,
                    answer_model: str = "openrouter/free") -> dict:
    """Retrieve evidence, then answer (LLM if a key exists, else local extraction)."""
    hits = search_document(question, document, top_k=top_k, candidate_pool=candidate_pool)
    answer = _llm_answer_from_hits(question, hits, history=None, answer_model=answer_model)
    if answer is None:
        answer = best_sentence_answer(question, hits)
    return {
        "answer": answer,
        "citations": extract_citations(answer, hits),
        "sources": build_sources(hits),
    }


def append_history(document: dict, question: str, result: dict) -> list[dict]:
    document.setdefault("history", []).append({
        "question": question,
        "answer": result.get("answer", ""),
        "citations": result.get("citations", []),
    })
    return document["history"]


# ---------------------------------------------------------------------------
# Simple retrieval evaluation
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Lab C: upload-time record, visible response, and multi-turn answering
# ---------------------------------------------------------------------------


def prepare_rag_chat_record(chat_id: str, filename: str, pdf_bytes: bytes | None = None,
                            pages: list[dict] | None = None, upload_root=None,
                            chunk_mode: str = "character_overlap", chunk_size: int = 700,
                            overlap: int = 120,
                            model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
                            batch_size: int = 32, artifact_root=None) -> dict:
    """Build the ``documents[chat_id]`` record for the upload route.

    Saves the uploaded PDF to ``upload_root/{chat_id}.pdf`` when bytes are
    given, then prepares the RAG record (pages, chunks, index, empty history).
    """
    if upload_root is None:
        upload_root = Path(__file__).resolve().parent.parent / "uploads"
    upload_root = Path(upload_root)
    upload_root.mkdir(parents=True, exist_ok=True)

    if pdf_bytes is not None and pages is None:
        pages = extract_pages_from_bytes_for_rag(pdf_bytes)
    if not pages:
        raise ValueError("PDF contains no readable text")

    document = prepare_rag_document(
        document_id=chat_id, filename=filename, pages=pages,
        chunk_mode=chunk_mode, chunk_size=chunk_size, overlap=overlap,
        model_name=model_name, batch_size=batch_size, artifact_root=artifact_root,
    )
    document["chat_id"] = chat_id
    document["history"] = []

    saved_pdf_path = upload_root / f"{chat_id}.pdf"
    if pdf_bytes is not None:
        saved_pdf_path.write_bytes(pdf_bytes)
    document["saved_pdf_path"] = str(saved_pdf_path)
    document["file_path"] = str(saved_pdf_path)
    return document


def build_upload_response(document: dict) -> dict:
    """Visible Day-2-shaped upload success JSON."""
    return {
        "status": "ok",
        "filename": document["filename"],
        "pages": len(document["pages"]),
        "characters": sum(len(page["text"]) for page in document["pages"]),
    }


def answer_document_turn(document: dict, question: str, top_k: int = 3,
                         candidate_pool: int = 60,
                         answer_model: str = "openrouter/free") -> dict:
    """Answer one question with fresh retrieval, then append to history."""
    history = document.get("history") or []
    hits = search_document(question, document, top_k=top_k, candidate_pool=candidate_pool,
                           history=history)
    answer = _llm_answer_from_hits(question, hits, history=history, answer_model=answer_model)
    if answer is None:
        answer = best_sentence_answer(question, hits)
    result = {
        "answer": answer,
        "citations": extract_citations(answer, hits),
        "sources": build_sources(hits),
    }
    append_history(document, question, result)
    result["history"] = document["history"]
    return result


def answer_chat_turn(document: dict, message: str, top_k: int = 3, candidate_pool: int = 60,
                     answer_model: str = "openrouter/free") -> dict:
    """Route-facing wrapper: fresh retrieval every turn + history update."""
    return answer_document_turn(document, message, top_k=top_k,
                                candidate_pool=candidate_pool, answer_model=answer_model)


def normalize_for_match(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (text or "").lower()).strip()


def contains_any_answer(text: str, answers: list[str]) -> bool:
    normalized = normalize_for_match(text)
    return any(normalize_for_match(answer) in normalized for answer in answers)


def evaluate_questions(eval_set: list[dict], documents_by_name: dict,
                       top_k: int = 3, candidate_pool: int = 60):
    """Return one table row per question with retrieval_hit / answer_hit."""
    import pandas as pd
    rows = []
    for item in eval_set:
        document = documents_by_name[item["pdf_name"]]
        hits = search_document(item["question"], document, top_k=top_k, candidate_pool=candidate_pool)
        local_answer = best_sentence_answer(item["question"], hits)
        retrieved_text = " ".join(hit["text"] for hit in hits)
        rows.append({
            "pdf_name": item["pdf_name"],
            "question": item["question"],
            "pages": sorted({hit["page"] for hit in hits}),
            "local_answer": local_answer,
            "retrieval_hit": contains_any_answer(retrieved_text, item["answers"]),
            "answer_hit": contains_any_answer(local_answer, item["answers"]),
        })
    return pd.DataFrame(rows)
