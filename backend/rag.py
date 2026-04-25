import re
from typing import List
import chromadb
from chromadb.utils import embedding_functions
from rank_bm25 import BM25Okapi

from deepseek_client import DeepSeekClient
from parser import detect_section


# DeepSeek does not host an embeddings endpoint, so we use ChromaDB's
# built-in ONNX MiniLM model (offline, no API key, ~25MB).  DeepSeek is
# kept for chat completions only.
_default_embed_fn = embedding_functions.DefaultEmbeddingFunction()


class HybridRetriever:
    """BM25 + semantic vector search merged via Reciprocal Rank Fusion."""

    def __init__(self, collection, corpus_docs: list[str], corpus_ids: list[str]):
        self.collection = collection
        self.corpus_ids = corpus_ids
        self.corpus_docs = corpus_docs
        tokenized = [HybridRetriever._tokenize(doc) for doc in corpus_docs]
        self.bm25 = BM25Okapi(tokenized) if tokenized else None

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        """CJK-aware tokenizer: character bigrams for CJK text, whitespace split for ASCII.

        Plain str.split() turns each Chinese phrase into one giant token, so BM25 scores
        are near-zero for Chinese queries.  Character bigrams give partial-match signal
        without requiring an external segmentation library.
        """
        text = re.sub(r'[：:，,。.？?！!、\s]+', ' ', text.lower()).strip()
        tokens: list[str] = []
        for word in text.split():
            if any('\u4e00' <= c <= '\u9fff' for c in word):
                # Bigrams for CJK characters
                for i in range(len(word) - 1):
                    tokens.append(word[i:i + 2])
                if word:  # also add unigram so single-char matches aren't lost
                    tokens.append(word)
            else:
                tokens.append(word)
        return [t for t in tokens if t.strip()]

    def retrieve(self, query: str, n: int = 5, where: dict = None) -> list[dict]:
        """Return top-n results merged from BM25 and semantic search via RRF."""
        actual_n = min(n, len(self.corpus_ids))
        if actual_n == 0:
            return []

        fetch_n = min(actual_n * 2, len(self.corpus_ids))

        # BM25 path — only keep positive-score items to avoid phantom RRF contributions
        bm25_ranked_ids: list[str] = []
        if self.bm25:
            scores = self.bm25.get_scores(HybridRetriever._tokenize(query))
            ranked_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
            bm25_ranked_ids = [
                self.corpus_ids[i] for i in ranked_indices if scores[i] > 0
            ][:fetch_n]

        # Semantic path via ChromaDB
        semantic_ids: list[str] = []
        try:
            kwargs: dict = {"query_texts": [query], "n_results": fetch_n}
            if where:
                kwargs["where"] = where
            results = self.collection.query(**kwargs)
            semantic_ids = (results.get("ids") or [[]])[0]
        except Exception:
            pass

        # RRF fusion
        k = 60
        candidate_ids = list(dict.fromkeys(bm25_ranked_ids + semantic_ids))
        bm25_rank_map = {doc_id: rank for rank, doc_id in enumerate(bm25_ranked_ids)}
        semantic_rank_map = {doc_id: rank for rank, doc_id in enumerate(semantic_ids)}

        rrf_scores: dict[str, float] = {}
        for doc_id in candidate_ids:
            score = 0.0
            if doc_id in bm25_rank_map:
                score += 1.0 / (k + bm25_rank_map[doc_id])
            if doc_id in semantic_rank_map:
                score += 1.0 / (k + semantic_rank_map[doc_id])
            rrf_scores[doc_id] = score

        top_ids = sorted(rrf_scores, key=lambda x: rrf_scores[x], reverse=True)[:actual_n]
        if not top_ids:
            return []

        try:
            fetched = self.collection.get(ids=top_ids, include=["documents", "metadatas"])
        except Exception:
            return []

        # Build a lookup keyed by id so we can iterate top_ids in RRF order.
        # ChromaDB's get() returns rows in storage/insertion order, NOT in the
        # order of the requested ids list, so iterating fetched["ids"] directly
        # would silently discard the relevance ranking.
        fetched_ids = fetched.get("ids", [])
        fetched_docs = fetched.get("documents", []) or []
        fetched_metas = fetched.get("metadatas", []) or []
        id_map = {
            did: (fetched_docs[j], fetched_metas[j] if j < len(fetched_metas) else {})
            for j, did in enumerate(fetched_ids)
        }
        return [
            {"id": did, "document": id_map[did][0], "metadata": id_map[did][1] or {}}
            for did in top_ids if did in id_map
        ]


class RAGSystem:
    def __init__(self, client: DeepSeekClient = None, embed_fn=None):
        self._chroma = chromadb.Client()  # in-memory, NOT PersistentClient
        self._embed_fn = embed_fn or _default_embed_fn
        self._qb_collection = None
        self._qb_retriever: HybridRetriever | None = None

    def seed_question_bank(self, questions: list[dict]):
        """Load question bank into ChromaDB. Called on startup."""
        try:
            self._chroma.delete_collection("question_bank")
        except Exception:
            pass

        collection = self._chroma.create_collection(
            name="question_bank",
            embedding_function=self._embed_fn
        )

        if not questions:
            return

        ids = [q["id"] for q in questions]
        documents = [f"{q['topic']}: {q['question']}" for q in questions]
        metadatas = [
            {
                "topic": q["topic"],
                "difficulty": q.get("difficulty", "medium"),
                "answer_guide": q.get("answer_guide", ""),
                "question": q["question"],
            }
            for q in questions
        ]

        collection.add(ids=ids, documents=documents, metadatas=metadatas)
        self._qb_collection = collection
        self._qb_retriever = HybridRetriever(collection, documents, ids)

    @staticmethod
    def _split_sentences(text: str) -> list[str]:
        parts = re.split(r'(?<=[。！？!?\n])', text)
        return [p.strip() for p in parts if len(p.strip()) > 10]

    def _build_parent_child_chunks(
        self, text: str, session_id: str, prefix: str, doc_type: str
    ) -> tuple[list[str], list[str], list[dict]]:
        """Build parent (paragraph) and child (sentence) chunks with metadata."""
        paragraphs = [p.strip() for p in text.split("\n\n") if len(p.strip()) > 20]
        if not paragraphs:
            paragraphs = [text[:500]]

        ids: list[str] = []
        docs: list[str] = []
        metas: list[dict] = []

        for p_idx, para in enumerate(paragraphs):
            parent_id = f"{prefix}_p{p_idx}"
            section = detect_section(para, doc_type)

            ids.append(parent_id)
            docs.append(para)
            metas.append({
                "chunk_type": "parent",
                "section": section,
                "chunk_index": p_idx,
                "session_id": session_id,
                "parent_id": parent_id,
            })

            sentences = self._split_sentences(para) or [para[:150]]
            for s_idx, sent in enumerate(sentences):
                ids.append(f"{parent_id}_c{s_idx}")
                docs.append(sent)
                metas.append({
                    "chunk_type": "child",
                    "section": section,
                    "chunk_index": s_idx,
                    "session_id": session_id,
                    "parent_id": parent_id,
                })

        return ids, docs, metas

    def index_resume(self, session_id: str, resume_text: str):
        """Chunk and index resume with parent-child chunks + section metadata."""
        try:
            self._chroma.delete_collection(f"resume_{session_id}")
        except Exception:
            pass

        collection = self._chroma.create_collection(
            name=f"resume_{session_id}",
            embedding_function=self._embed_fn
        )
        ids, docs, metas = self._build_parent_child_chunks(
            resume_text, session_id, f"resume_{session_id}", "resume"
        )
        collection.add(ids=ids, documents=docs, metadatas=metas)

    def index_jd(self, session_id: str, jd_text: str):
        """Chunk and index JD with parent-child chunks + section metadata."""
        try:
            self._chroma.delete_collection(f"jd_{session_id}")
        except Exception:
            pass

        collection = self._chroma.create_collection(
            name=f"jd_{session_id}",
            embedding_function=self._embed_fn
        )
        ids, docs, metas = self._build_parent_child_chunks(
            jd_text, session_id, f"jd_{session_id}", "jd"
        )
        collection.add(ids=ids, documents=docs, metadatas=metas)

    def retrieve_questions(self, session_id: str, topic: str, n_results: int = 5) -> list[dict]:
        """Retrieve relevant questions using hybrid search (BM25 + semantic + RRF)."""
        if self._qb_collection is None:
            try:
                self._qb_collection = self._chroma.get_collection(
                    "question_bank", embedding_function=self._embed_fn
                )
                fetched = self._qb_collection.get(include=["documents"])
                self._qb_retriever = HybridRetriever(
                    self._qb_collection,
                    fetched.get("documents", []),
                    fetched.get("ids", []),
                )
            except Exception:
                return []

        if self._qb_retriever is None:
            return []

        where = {"topic": topic} if topic else None
        results = self._qb_retriever.retrieve(topic, n=n_results, where=where)

        questions = []
        for r in results:
            meta = r.get("metadata", {})
            questions.append({
                "topic": meta.get("topic", ""),
                "question": meta.get("question", ""),
                "difficulty": meta.get("difficulty", "medium"),
                "answer_guide": meta.get("answer_guide", ""),
            })
        return questions

    def _retrieve_parent_context(
        self, collection, query: str, n: int = 3
    ) -> list[dict]:
        """Query child chunks, expand to parent chunks for richer context."""
        try:
            count = collection.count()
            if count == 0:
                return []
            results = collection.query(
                query_texts=[query],
                n_results=min(n * 2, count),
                where={"chunk_type": "child"},
            )
        except Exception:
            return []

        if not results or not results.get("ids"):
            return []

        parent_ids: list[str] = []
        seen: set[str] = set()
        for meta in (results.get("metadatas") or [[]])[0]:
            pid = (meta or {}).get("parent_id")
            if pid and pid not in seen:
                seen.add(pid)
                parent_ids.append(pid)
                if len(parent_ids) >= n:
                    break

        if not parent_ids:
            return []

        try:
            fetched = collection.get(ids=parent_ids, include=["documents", "metadatas"])
        except Exception:
            return []

        # Preserve semantic-rank order (parent_ids was built best-first from child query).
        # ChromaDB get() returns storage order, not requested-id order.
        fetched_ids = fetched.get("ids", [])
        fetched_docs = fetched.get("documents", []) or []
        fetched_metas = fetched.get("metadatas", []) or []
        id_map = {
            did: (fetched_docs[j], fetched_metas[j] if j < len(fetched_metas) else {})
            for j, did in enumerate(fetched_ids)
        }
        out = []
        for doc_id in parent_ids:
            if doc_id in id_map:
                text, meta = id_map[doc_id]
                out.append({
                    "id": doc_id,
                    "text": text,
                    "section": (meta or {}).get("section", "general"),
                })
        return out

    def retrieve_resume_context(self, session_id: str, query: str, n: int = 3) -> list[dict]:
        """Retrieve relevant resume sections via parent-child lookup."""
        try:
            col = self._chroma.get_collection(
                f"resume_{session_id}", embedding_function=self._embed_fn
            )
        except Exception:
            return []
        return self._retrieve_parent_context(col, query, n)

    def retrieve_jd_context(self, session_id: str, query: str, n: int = 3) -> list[dict]:
        """Retrieve relevant JD sections via parent-child lookup."""
        try:
            col = self._chroma.get_collection(
                f"jd_{session_id}", embedding_function=self._embed_fn
            )
        except Exception:
            return []
        return self._retrieve_parent_context(col, query, n)

    def cleanup_session(self, session_id: str):
        """Remove session-specific collections."""
        for name in [f"resume_{session_id}", f"jd_{session_id}"]:
            try:
                self._chroma.delete_collection(name)
            except Exception:
                pass


rag_system = RAGSystem()
