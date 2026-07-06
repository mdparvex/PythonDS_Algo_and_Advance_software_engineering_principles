# Retrieval-Augmented Generation (RAG): End-to-End Engineering Guide

> A practical, architecture-first guide to building production RAG systems — from first principles to a complete reference project.

---

## Table of Contents

1. [Why RAG Exists](#1-why-rag-exists)
2. [Mental Model: The Two Pipelines](#2-mental-model-the-two-pipelines)
3. [End-to-End Architecture](#3-end-to-end-architecture)
4. [Component Deep Dives](#4-component-deep-dives)
   - 4.1 Document Ingestion & Loading
   - 4.2 Chunking Strategies
   - 4.3 Embeddings
   - 4.4 Vector Stores & Indexing
   - 4.5 Retrieval (Dense, Sparse, Hybrid)
   - 4.6 Reranking
   - 4.7 Context Assembly & Prompting
   - 4.8 Generation & Grounding
5. [Advanced Retrieval Patterns](#5-advanced-retrieval-patterns)
6. [Evaluation](#6-evaluation)
7. [Production Concerns](#7-production-concerns)
8. [Sample Project: Clinical Drug Information & Interaction Assistant](#8-sample-project-clinical-drug-information--interaction-assistant)
9. [Common Failure Modes & Fixes](#9-common-failure-modes--fixes)
10. [Decision Cheat Sheet](#10-decision-cheat-sheet)

---

## 1. Why RAG Exists

A large language model is a fixed function: it maps a prompt to a probability distribution over the next token, using weights frozen at training time. That single fact creates four hard limitations:

**Knowledge cutoff.** The model knows nothing after its training date. It cannot tell you about a drug approved last month or a policy your company published yesterday.

**No private knowledge.** The model never saw your internal documents, your customer database, or your proprietary research. This information does not exist in its weights.

**Hallucination.** When the model lacks knowledge, it does not say "I don't know" — it generates the most *plausible-sounding* continuation, which is frequently wrong but fluent. This is fatal in high-stakes domains.

**No provenance.** A raw LLM answer cannot be traced back to a source. In medicine, law, or finance, an unsourced claim is unusable.

You have three ways to inject external knowledge into an LLM:

| Approach | What it does | Cost | Freshness | Provenance | Best for |
|---|---|---|---|---|---|
| **Fine-tuning** | Bakes knowledge into weights | High (training runs) | Stale (retrain to update) | None | Teaching *behavior/style/format*, not facts |
| **Long context** | Stuff everything into the prompt | High (tokens per call) | Fresh | Weak | Small, bounded corpora |
| **RAG** | Retrieve relevant snippets, inject at query time | Low-moderate | Fresh (update the index) | Strong (cite chunks) | Large, changing knowledge bases |

**RAG's core insight:** don't try to make the model *know* everything. Make it *look things up* at answer time, and force it to answer *only* from what it retrieved. This turns a closed-book exam into an open-book exam — and open-book is dramatically more reliable for factual work.

A crucial framing that prevents a common mistake: **fine-tuning changes how the model behaves; RAG changes what the model knows.** They are complementary, not competing. You fine-tune to teach a model to output structured clinical notes in your house format; you use RAG to give it the actual patient's medication list. Reaching for fine-tuning to fix a *knowledge* gap is the single most common architectural error teams make.

---

## 2. Mental Model: The Two Pipelines

Every RAG system is two pipelines that run at different times and are easy to conflate. Keeping them mentally separate is the single most useful thing you can do.

**Pipeline A — Indexing (offline, batch).** Runs ahead of time, whenever your source documents change. It transforms raw documents into a searchable index. Slow, expensive, and infrequent is fine here.

```
Raw docs → Load → Clean → Chunk → Embed → Store in vector DB (+ metadata)
```

**Pipeline B — Query (online, real-time).** Runs on every user request. It must be fast. It takes a question, finds relevant chunks, and generates a grounded answer.

```
Query → Transform → Retrieve → Rerank → Assemble context → Generate → Post-process → Answer + citations
```

The two pipelines meet at exactly one place: **the vector store.** Indexing writes to it; querying reads from it. If you internalize nothing else, internalize that these are separate systems with separate performance budgets, separate scaling characteristics, and often separate deployment cadences.

---

## 3. End-to-End Architecture

Here is the full system, with the offline and online paths shown together and the data store as the shared boundary.

```
┌─────────────────────────── OFFLINE: INDEXING PIPELINE ───────────────────────────┐
│                                                                                   │
│  Data Sources        Loaders         Preprocess       Chunker        Embedder     │
│  ┌──────────┐      ┌──────────┐     ┌──────────┐    ┌──────────┐   ┌──────────┐   │
│  │ PDFs     │────▶│ Extract  │────▶│ Clean,   │──▶│ Split    │──▶│ Encode   │   │
│  │ DBs      │      │ text +   │     │ normalize│    │ into     │   │ each     │   │
│  │ APIs     │      │ metadata │     │ dedupe   │    │ chunks   │   │ chunk    │   │
│  │ HTML     │      └──────────┘     └──────────┘    └──────────┘   └────┬─────┘   │
│  └──────────┘                                                           │         │
│                                                                         ▼         │
│                                                          ┌─────────────────────┐  │
│                                                          │   VECTOR STORE      │  │
│                                                          │  vectors + text +   │  │
│                                                          │  metadata + BM25    │  │
│                                                          │      index          │  │
│                                                          └─────────┬───────────┘  │
└────────────────────────────────────────────────────────────────────│──────────────┘
                                                                     │
┌────────────────────────── ONLINE: QUERY PIPELINE ───────────────── │ ────────────┐
│                                                                    │             │
│  User Query    Query Transform    Retrieve            Rerank       │  Generate   │
│  ┌────────┐   ┌─────────────┐   ┌──────────┐      ┌──────────┐     │ ┌────────┐  │
│  │ "..."  │─▶│ rewrite,    │──▶│ dense +  │◀────┤ cross-   │◀────┘ │ LLM    │  │
│  │        │   │ expand,     │   │ sparse   │      │ encoder  │       │ with   │  │
│  │        │   │ decompose   │   │ hybrid   │───▶ │ reorder  │──────▶│ context│  │
│  └────────┘   └─────────────┘   └──────────┘      │ top-k    │       │        │  │
│                                                   └──────────┘       └───┬────┘  │
│                                                                           │      │
│                                                          ┌────────────────▼────┐ │
│                                                          │ Answer + citations  │ │
│                                                          │ + guardrail checks  │ │
│                                                          └─────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────────────┘
```

Read it as a flow of transformations. On the left, heterogeneous source data is normalized into a uniform stream of text-plus-metadata. That stream is chunked and embedded into vectors, which land in the store alongside their original text and a keyword (BM25) index. At query time, the user's question is transformed, used to retrieve candidates by both vector similarity and keyword match, reranked for precision, assembled into a prompt, and handed to the LLM — which produces a grounded, cited answer that is finally checked by guardrails.

Every arrow is a place where quality can be won or lost. The following sections walk each one.

---

## 4. Component Deep Dives

### 4.1 Document Ingestion & Loading

The goal of ingestion is to turn every source format into a normalized internal representation: **text content plus structured metadata**. Metadata is not an afterthought — it is what lets you filter ("only guidelines published after 2023", "only cardiology") and cite ("source: BNF §2.5, page 412").

Common source-specific pitfalls:

- **PDFs** are the worst offenders. Text may be in reading order or in visual (column) order; tables shatter into gibberish; scanned PDFs are images requiring OCR. Use a layout-aware parser (e.g., `unstructured`, `pymupdf` with care, or a document-AI service) rather than naive text extraction.
- **HTML** carries navigation, ads, and boilerplate. Strip to main content; preserve heading structure because it encodes hierarchy you'll want for chunking.
- **Structured data (DBs, CSVs, JSON)** should usually be *templated into prose* ("Drug: Amlodipine. Class: calcium channel blocker. Adult dose: ...") rather than embedded as raw rows — embeddings work far better on natural language than on `{"col": "val"}`.

Attach at minimum: `source_id`, `document_title`, `section`, `page/anchor`, `published_date`, `content_type`, and any domain filters (specialty, jurisdiction, product line).

### 4.2 Chunking Strategies

Chunking is the highest-leverage, most-underestimated decision in the whole system. You are splitting documents into retrievable units. Chunk too large and you dilute the signal (the relevant sentence drowns in irrelevant context, and you waste tokens). Chunk too small and you fragment meaning (a chunk says "the recommended dose is 5mg" but not *of what*).

**Fixed-size chunking.** Split every N tokens with an overlap of ~10–20%. Simple, fast, format-agnostic. The overlap prevents a concept from being severed at a boundary. Weakness: it's blind to structure and cheerfully cuts mid-sentence and mid-table.

**Recursive character splitting.** Try to split on the largest natural boundary first (paragraphs), then fall back to sentences, then words, until chunks fit the size budget. This respects structure far better than fixed-size and is the sensible default for prose.

**Document-aware / structural chunking.** Split on the document's own hierarchy — Markdown headers, HTML sections, legal clause numbers. Each chunk carries its heading path as metadata ("Chapter 2 > Cardiovascular > Beta-blockers"). Excellent when documents are well-structured.

**Semantic chunking.** Embed sentences, then start a new chunk wherever the topic shifts (measured by a drop in cosine similarity between adjacent sentences). Produces topically coherent chunks at the cost of an embedding pass during indexing.

**A practical rule:** start with recursive splitting at ~400–800 tokens with ~15% overlap, then measure. Chunk size interacts with your embedding model's optimal input length and your reranker's context window. There is no universally correct number — it is an empirical parameter you tune against your eval set.

One powerful refinement — **contextual chunking** — prepends a short, LLM-generated description of where each chunk sits in its parent document before embedding it ("This chunk is from the 2024 hypertension guideline, section on elderly patients, and discusses..."). This measurably improves retrieval because an isolated chunk often loses the context that makes it findable.

### 4.3 Embeddings

An embedding model maps text to a dense vector such that semantically similar texts land near each other in vector space. Similarity is measured by cosine distance. This is what lets "chest pain medication" retrieve a chunk about "angina therapy" even with zero shared words — the semantic gap that keyword search cannot cross.

Key concepts:

- **Bi-encoder** (what embeddings are): query and document are encoded *independently* into vectors, then compared by cheap distance math. This is what makes retrieval scalable — you embed millions of documents once, offline, and only embed the query at run time.
- **Dimensionality** (e.g., 384, 768, 1536): higher dims can capture more nuance but cost more storage and compute. Diminishing returns are real.
- **Domain fit matters enormously.** A general-purpose embedding model may not know that "MI" means myocardial infarction. In specialized domains, a domain-tuned embedding model (or a fine-tuned one) often beats a larger general model.
- **Asymmetric search.** Questions and documents look different. Some models expect a task prefix (e.g., `"query: ..."` vs `"passage: ..."`). Using the wrong prefix silently degrades quality — check the model card.

**Critical operational rule:** the *same* embedding model must be used for indexing and for querying. If you change the model, you must re-index the entire corpus. Vectors from different models live in incompatible spaces.

### 4.4 Vector Stores & Indexing

A vector store holds your vectors and answers "give me the k nearest vectors to this query vector" — fast, over millions of items. Doing this *exactly* (comparing against every vector) is too slow at scale, so vector DBs use **Approximate Nearest Neighbor (ANN)** indexes that trade a tiny amount of recall for enormous speed.

Two dominant index families:

- **HNSW (Hierarchical Navigable Small World):** a layered graph you traverse greedily. Excellent recall/latency, higher memory. The default in most modern systems.
- **IVF (Inverted File Index):** partition vectors into clusters; at query time, search only the nearest few clusters. More memory-efficient, tunable, slightly more setup.

What actually matters when choosing a store:

- **Metadata filtering** (pre-filter vs post-filter): can you say "nearest vectors *where specialty = cardiology and date > 2023*" efficiently? Pre-filtering (filter, then search) is what you want; naive post-filtering can return too few results.
- **Hybrid search support:** built-in BM25 + vectors with fusion.
- **Operational model:** managed (Pinecone) vs self-hosted (Qdrant, Weaviate, Milvus) vs library/embedded (FAISS, Chroma) vs "just use Postgres" (`pgvector`). For many teams `pgvector` is the right first choice — one fewer system to run, and transactional consistency with your existing data.

### 4.5 Retrieval (Dense, Sparse, Hybrid)

Retrieval finds candidate chunks for a query. Three approaches, and you almost always want the third.

**Dense retrieval** uses embedding similarity. Strength: semantic matching, synonyms, paraphrases. Weakness: it can miss exact terms — drug codes, dosages, rare proper nouns, error codes — precisely the tokens where an exact match matters most.

**Sparse retrieval (BM25/keyword)** ranks by term overlap with clever weighting (rare words count more; it saturates term frequency). Strength: exact matches, jargon, identifiers, numbers. Weakness: zero semantic understanding — "heart attack" won't match "myocardial infarction".

**Hybrid retrieval** runs both and fuses the results. Dense catches meaning; sparse catches exact terms. The fusion is usually **Reciprocal Rank Fusion (RRF)**, which combines ranked lists without needing the two scoring systems to be on the same scale:

```
RRF_score(doc) = Σ  1 / (k + rank_i(doc))     # summed over each retriever i; k ≈ 60
```

A document ranked highly by *either* retriever floats to the top. Hybrid retrieval is the reliable default for real-world corpora because real queries mix semantic intent with specific terms — "what's the pediatric dose of amoxicillin for otitis media" needs both the semantics of "pediatric dose" and the exact terms "amoxicillin" and "otitis media".

### 4.6 Reranking

Retrieval is tuned for *recall* — cast a wide net, fetch maybe 50–100 candidates, don't miss the good ones. But you can only fit a handful into the prompt, and you want the *best* few at the top. That's reranking: a *precision* step.

A **cross-encoder** reranker takes the query and each candidate *together* and scores their relevance directly. Because it sees both texts jointly (unlike the bi-encoder, which encoded them separately), it's far more accurate at judging relevance — at the cost of being far slower. That cost is acceptable because you only run it on the ~100 candidates retrieval already narrowed to, not the whole corpus.

The two-stage pattern — **cheap wide retrieval → expensive narrow reranking** — is one of the most reliable quality wins in RAG. Retrieve 100, rerank, keep the top 5. Teams that skip reranking and feed raw vector-search results to the LLM leave a lot of accuracy on the table.

### 4.7 Context Assembly & Prompting

Now assemble the reranked chunks into a prompt. This is where grounding is enforced. Principles:

- **Instruct the model to answer only from the context**, and to say it doesn't know when the context is insufficient. This is your primary defense against hallucination.
- **Label each chunk with an ID** so the model can cite it, and require citations in the output.
- **Order matters.** Models attend more to the beginning and end of long contexts (the "lost in the middle" effect). Put the strongest chunks at the edges.
- **Budget your tokens.** Reserve room for the answer. Deduplicate near-identical chunks. Don't blindly stuff — more context is not always better and can *lower* accuracy by burying the signal.

A robust system prompt skeleton:

```
You are a clinical information assistant. Answer the question using ONLY the
numbered sources below. Every factual claim must cite its source as [n].
If the sources do not contain the answer, say so explicitly and do not guess.
Do not use prior knowledge beyond the sources.

Sources:
[1] {chunk_1}   (from: {citation_1})
[2] {chunk_2}   (from: {citation_2})
...

Question: {user_question}
```

### 4.8 Generation & Grounding

The LLM generates the final answer from the assembled prompt. But generation isn't the end — post-processing is what makes the output trustworthy:

- **Citation validation:** verify every `[n]` the model emitted actually exists and, ideally, that the cited chunk supports the claim (a second LLM or NLI model can check entailment).
- **Guardrails:** in regulated domains, scan for unsafe patterns (e.g., a dosage recommendation without a required safety caveat) before the answer reaches the user.
- **Refusal handling:** if retrieval returned nothing relevant, short-circuit and return "I don't have information on that" rather than letting the model improvise.

This closes the loop: retrieved evidence in, grounded and verified answer out.


---

## 5. Advanced Retrieval Patterns

Basic RAG (embed query → search → stuff → generate) fails on hard queries. These patterns address specific failure modes. Reach for them when your eval set shows the corresponding weakness — not preemptively.

**Query rewriting / expansion.** User queries are messy, terse, or conversational ("what about kids?" after a discussion of dosing). Use an LLM to rewrite the query into a standalone, retrieval-optimized form, or generate several paraphrases and retrieve for each (**multi-query retrieval**), then merge. Fixes: poorly-phrased queries missing good chunks.

**HyDE (Hypothetical Document Embeddings).** Instead of embedding the *question*, ask an LLM to write a hypothetical *answer*, then embed *that* and search. The hypothetical answer lives in the same "document space" as your corpus, so it often retrieves better than a bare question. Fixes: the vocabulary mismatch between how people ask and how documents state.

**Query decomposition.** A complex question ("does drug A interact with drug B, and is either contraindicated in pregnancy?") contains multiple sub-questions. Decompose into atomic queries, retrieve for each independently, then synthesize. Fixes: multi-hop questions where no single chunk holds the whole answer. **This is essential for the sample project's interaction-checking feature.**

**Parent-document / small-to-big retrieval.** Index small chunks (precise matching) but, on a hit, return the larger *parent* section (fuller context for generation). You search with a scalpel and answer with a paragraph. Fixes: the small-chunk-vs-large-chunk tension from §4.2.

**Self-query / metadata extraction.** Use an LLM to parse a natural-language query into a semantic part *plus* structured filters ("papers on statins after 2022" → search:"statins", filter:`date > 2022`). Fixes: queries that mix meaning with hard constraints.

**Agentic RAG.** Wrap retrieval in a loop: the model retrieves, judges whether it has enough, and retrieves again with a refined query if not — possibly across multiple tools/indexes. More capable and more expensive; use when single-shot retrieval genuinely can't answer multi-step questions.

**GraphRAG.** Build a knowledge graph (entities + relationships) from the corpus and retrieve over graph structure, not just vector similarity. Excels at "connect-the-dots" questions spanning many documents ("what themes recur across all incident reports?") that flat retrieval can't assemble. Heavier to build; powerful for global/aggregative questions.

---

## 6. Evaluation

You cannot improve what you don't measure, and RAG has *two* systems to measure — retrieval and generation — because a good answer requires both a good retrieval and good use of it. Debugging without splitting these is guesswork.

### Retrieval metrics (did we fetch the right chunks?)

Build a test set of `(question, known-relevant chunk IDs)` pairs, then measure:

- **Context Recall / Recall@k** — of the chunks that *should* have been retrieved, what fraction were in the top k? The most important retrieval metric: if the answer isn't retrieved, generation cannot recover.
- **Context Precision / MRR** — are the relevant chunks ranked near the *top*? Rewards good ordering (which matters because of context limits and lost-in-the-middle).
- **NDCG** — graded relevance with position discounting, when chunks have degrees of relevance rather than binary.

### Generation metrics (did we answer well from what we fetched?)

- **Faithfulness / groundedness** — is every claim in the answer supported by the retrieved context? This directly measures hallucination. Usually scored by an LLM-as-judge or an NLI model checking entailment.
- **Answer relevance** — does the answer actually address the question (vs. being true but off-topic)?
- **Context relevance** — how much of the retrieved context was actually useful? Low values signal noisy retrieval.

Frameworks like **RAGAS** and **TruLens** operationalize these, typically using an LLM as judge. The classic decomposition — often called the "RAG triad" — is *context relevance* (retrieval quality) → *groundedness* (is the answer supported?) → *answer relevance* (does it address the question?). If groundedness is high but answer relevance is low, your retrieval is fine and your prompt is weak. If groundedness is low, your model is inventing — tighten the prompt or improve retrieval. This triad tells you *which half* to fix.

### Building the test set

Bootstrap it: have an LLM read chunks and generate plausible questions each chunk answers, then have humans validate a sample. Fifty well-chosen questions covering your real query distribution beat a thousand random ones. Version this set and re-run it on every change — RAG systems regress silently, and an eval set is your regression suite.

---

## 7. Production Concerns

**Latency budget.** Each stage adds delay: query rewrite (LLM call), embed (fast), retrieve (fast), rerank (moderate), generate (slow, dominant). Parallelize what you can. Cache aggressively. Stream the generation so users see tokens immediately. Consider skipping expensive stages (rewrite, rerank) for easy queries via a fast classifier.

**Caching.** Cache at multiple layers: embedding cache (identical query text → reuse vector), retrieval cache (same query → same chunks for a TTL), and semantic cache (near-identical questions → reuse the whole answer). Caching is often the biggest single latency and cost win.

**Cost.** Dominated by LLM generation tokens, then embedding calls during indexing. Control it with smaller models for easy queries, tight context budgets, caching, and reranking (fewer, better chunks = fewer tokens).

**Incremental indexing.** Re-embedding everything on every document change doesn't scale. Track document versions/hashes; only re-chunk and re-embed what changed. Support deletes (a removed source document must leave the index). This is a real engineering system, not a one-off script.

**Security & access control.** Two big ones. (1) **Document-level authorization:** a user must only retrieve chunks they're allowed to see — enforce with metadata filters tied to the caller's identity, *before* retrieval. Never rely on the LLM to withhold retrieved data. (2) **Prompt injection:** retrieved documents are untrusted input; a malicious chunk can carry instructions ("ignore previous instructions and..."). Treat retrieved content as data, not commands; sandbox it in the prompt; never let it trigger tool calls unchecked.

**Observability.** Log the full trace per query: rewritten query, retrieved chunk IDs + scores, reranked order, final prompt, model output, latency per stage. When an answer is wrong, this trace tells you *which stage* failed. Without it you're blind.

**The freshness/consistency gap.** Between a document changing and its chunks being re-indexed, your system serves stale answers. Define an acceptable staleness SLA and build indexing cadence to meet it.


---

## 8. Sample Project: Clinical Drug Information & Interaction Assistant

### 8.1 The Problem

Clinicians and pharmacists need to answer questions like these, correctly and fast, at the point of care:

- *"What's the recommended adult dose of amlodipine for hypertension, and how do I adjust it in renal impairment?"*
- *"Is it safe to co-prescribe clarithromycin with simvastatin?"*
- *"My patient is pregnant and on losartan — what are the concerns and alternatives?"*

Getting these wrong causes real harm. The answers live scattered across drug monographs, clinical guidelines, and interaction databases — each large, frequently updated, and written in dense clinical language. A raw LLM is dangerous here: it will confidently invent doses and miss interactions. This is a textbook RAG problem, but a *hard* one, because:

1. **Exactness is non-negotiable** — "5 mg" vs "50 mg" is the difference between therapy and overdose. (Demands hybrid retrieval; dense-only will blur numbers and codes.)
2. **Interaction queries are multi-hop** — you must retrieve information about drug A *and* drug B *and* the interaction between them, then synthesize. (Demands query decomposition.)
3. **Answers must be cited and safe** — every claim traces to a source, and unsafe outputs are blocked. (Demands grounding + guardrails.)
4. **Context matters** — pediatric vs adult, pregnancy, renal/hepatic impairment change the answer. (Demands metadata filtering.)

> ⚠️ This is a reference architecture for education. A real clinical tool requires clinical validation, regulatory clearance, and human-in-the-loop sign-off. Never ship unsupervised clinical advice.

### 8.2 System Architecture

```
                          ┌─────────────────────────────────────────┐
                          │           FastAPI Service               │
                          │                                         │
  Clinician ──query─────▶│  /ask   endpoint                         │
                          │    │                                    │
                          │    ▼                                    │
                          │  Query Router ── is it an interaction?  │
                          │    │                    │               │
                          │    │ simple             │ interaction   │
                          │    ▼                    ▼               │
                          │  Query           Decompose into         │
                          │  Rewrite         per-drug + pairwise    │
                          │    │             sub-queries            │
                          │    └────────┬───────────┘               │
                          │             ▼                           │
                          │    ┌───────────────────┐                │
                          │    │ Hybrid Retriever  │◀──── Qdrant    │
                          │    │ dense + BM25 + RRF│     (vectors   │
                          │    │ + metadata filter │      + text    │
                          │    └────────┬──────────┘     + payload) │
                          │             ▼                           │
                          │    ┌───────────────────┐                │
                          │    │ Cross-Encoder     │                │
                          │    │ Reranker (top-k)  │                │
                          │    └────────┬──────────┘                │
                          │             ▼                           │
                          │    ┌────────────────────┐               │
                          │    │ Grounded Generator │──── LLM       │
                          │    │ + citation enforce │               │
                          │    └────────┬───────────┘               │
                          │             ▼                           │
                          │    ┌───────────────────┐                │
                          │    │ Safety Guardrails │                │
                          │    │ + citation verify │                │
                          │    └────────┬──────────┘                │
                          │             ▼                           │
                          └─────────── Answer + citations ──────────┘

  ┌──────────────── OFFLINE INDEXING (separate job) ────────────────┐
  │  Monographs (structured) ─┐                                     │
  │  Guidelines (PDF)         ├─▶ Load ─▶ Chunk ─▶ Embed ─▶ Qdrant│
  │  Interaction DB (table)  ─┘   (templated + contextual chunking) │
  └─────────────────────────────────────────────────────────────────┘
```

### 8.3 Project Structure (Clean Architecture)

```
clinical_rag/
├── domain/                     # Pure business objects, no dependencies
│   ├── models.py               #   Document, Chunk, RetrievedChunk, Answer, Citation
│   └── ports.py                #   Abstract interfaces (Embedder, VectorStore, Reranker, LLM)
├── ingestion/                  # OFFLINE pipeline
│   ├── loaders.py              #   monograph, guideline (PDF), interaction-table loaders
│   ├── chunker.py              #   structural + contextual chunking
│   └── index_job.py            #   orchestrates load → chunk → embed → upsert
├── retrieval/                  # ONLINE retrieval
│   ├── embedder.py             #   sentence-transformers adapter
│   ├── vector_store.py         #   Qdrant adapter (hybrid + filtered search)
│   ├── reranker.py             #   cross-encoder adapter
│   ├── query_transform.py      #   rewrite + interaction decomposition
│   └── retriever.py            #   orchestrates hybrid retrieve → RRF → rerank
├── generation/
│   ├── prompts.py              #   grounded prompt templates
│   ├── generator.py            #   LLM adapter + citation enforcement
│   └── guardrails.py           #   safety checks + citation verification
├── api/
│   ├── main.py                 #   FastAPI app, dependency wiring
│   └── schemas.py              #   Pydantic request/response
├── eval/
│   ├── testset.py              #   golden Q→relevant-chunk pairs
│   └── run_eval.py             #   recall@k, MRR, faithfulness
└── config.py
```

This mirrors the two-pipeline mental model: `ingestion/` is offline, `retrieval/` + `generation/` are online, `domain/` holds shared contracts, and adapters (Qdrant, embedder, LLM) sit behind interfaces so any one is swappable without touching business logic.

### 8.4 Domain Models & Ports

```python
# domain/models.py
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum

class ContentType(str, Enum):
    MONOGRAPH = "monograph"
    GUIDELINE = "guideline"
    INTERACTION = "interaction"

@dataclass
class Chunk:
    id: str
    text: str
    # metadata drives filtering AND citation
    drug_names: list[str] = field(default_factory=list)
    content_type: ContentType = ContentType.MONOGRAPH
    section: str = ""
    source_title: str = ""
    source_ref: str = ""          # e.g. "BNF 2024, §2.5, p.412" — used in citations
    population: list[str] = field(default_factory=list)  # e.g. ["adult","renal_impairment"]
    published_date: str = ""

@dataclass
class RetrievedChunk:
    chunk: Chunk
    score: float

@dataclass
class Citation:
    ref: str
    source_title: str
    chunk_id: str

@dataclass
class Answer:
    text: str
    citations: list[Citation]
    used_chunks: list[str]
    safe: bool = True
    warnings: list[str] = field(default_factory=list)
```

```python
# domain/ports.py — interfaces the rest of the system depends on
from abc import ABC, abstractmethod
from domain.models import Chunk, RetrievedChunk

class Embedder(ABC):
    @abstractmethod
    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...
    @abstractmethod
    def embed_query(self, text: str) -> list[float]: ...

class VectorStore(ABC):
    @abstractmethod
    def upsert(self, chunks: list[Chunk], vectors: list[list[float]]) -> None: ...
    @abstractmethod
    def hybrid_search(
        self, query_text: str, query_vector: list[float],
        top_k: int, filters: dict | None = None,
    ) -> list[RetrievedChunk]: ...

class Reranker(ABC):
    @abstractmethod
    def rerank(self, query: str, candidates: list[RetrievedChunk], top_k: int
    ) -> list[RetrievedChunk]: ...

class LLM(ABC):
    @abstractmethod
    def complete(self, system: str, user: str, temperature: float = 0.0) -> str: ...
```

Everything downstream depends on these abstractions, never on Qdrant or a specific model — the dependency-inversion principle that keeps the core testable and vendor-swappable.

### 8.5 Ingestion — Templating & Contextual Chunking

The key move: structured drug data is **templated into prose** before chunking (embeddings work better on language than on key-value rows), and each chunk is **prefixed with context** so it's findable in isolation.

```python
# ingestion/loaders.py
from domain.models import Chunk, ContentType

def load_monograph(record: dict) -> list[Chunk]:
    """A structured drug record -> one chunk per clinically meaningful section.
    Templating raw fields into sentences dramatically improves retrieval."""
    drug = record["generic_name"]
    base = dict(
        drug_names=[drug] + record.get("brand_names", []),
        content_type=ContentType.MONOGRAPH,
        source_title=record["source_title"],
        published_date=record["published_date"],
    )
    chunks: list[Chunk] = []

    # Dosage section — note population metadata for later filtering
    for pop, dose in record["dosing"].items():   # e.g. {"adult": "...", "renal_impairment": "..."}
        text = (
            f"Drug: {drug} ({record['drug_class']}). "
            f"Population: {pop.replace('_', ' ')}. "
            f"Dosing: {dose}."
        )
        chunks.append(Chunk(
            id=f"{drug}:dose:{pop}", text=text, section="Dosage",
            population=[pop], source_ref=f"{record['source_title']} — Dosing ({pop})",
            **base,
        ))

    # Contraindications, pregnancy, etc. — one chunk each, same pattern
    for section_key, section_label in [
        ("contraindications", "Contraindications"),
        ("pregnancy", "Pregnancy & Lactation"),
        ("adverse_effects", "Adverse Effects"),
    ]:
        if record.get(section_key):
            chunks.append(Chunk(
                id=f"{drug}:{section_key}", section=section_label,
                text=f"Drug: {drug}. {section_label}: {record[section_key]}",
                source_ref=f"{record['source_title']} — {section_label}",
                population=["pregnancy"] if section_key == "pregnancy" else [],
                **base,
            ))
    return chunks


def load_interaction(record: dict) -> Chunk:
    """One chunk per drug PAIR. Storing both directions as searchable text
    is what makes pairwise interaction retrieval work."""
    a, b = record["drug_a"], record["drug_b"]
    text = (
        f"Drug interaction between {a} and {b}. "
        f"Severity: {record['severity']}. "
        f"Mechanism: {record['mechanism']}. "
        f"Management: {record['management']}."
    )
    return Chunk(
        id=f"interaction:{a}:{b}", text=text, section="Interaction",
        drug_names=[a, b], content_type=ContentType.INTERACTION,
        source_title=record["source_title"], source_ref=record["source_ref"],
        published_date=record["published_date"],
    )
```

```python
# ingestion/chunker.py
def add_contextual_prefix(chunk: Chunk) -> Chunk:
    """Prepend a locating sentence so the chunk is retrievable out of context.
    (Cheap version; production can use an LLM to generate richer context.)"""
    prefix = (
        f"[Context: {chunk.section} section for "
        f"{', '.join(chunk.drug_names[:2])} "
        f"from {chunk.source_title}] "
    )
    chunk.text = prefix + chunk.text
    return chunk
```

```python
# ingestion/index_job.py
def run_indexing(records, loaders, chunker, embedder, store, batch_size=128):
    all_chunks: list[Chunk] = []
    for rec in records:
        all_chunks.extend(loaders[rec["type"]](rec))
    all_chunks = [chunker(c) for c in all_chunks]

    for i in range(0, len(all_chunks), batch_size):
        batch = all_chunks[i:i + batch_size]
        vectors = embedder.embed_documents([c.text for c in batch])
        store.upsert(batch, vectors)          # idempotent on chunk.id -> safe re-runs
    print(f"Indexed {len(all_chunks)} chunks")
```

Note the idempotent upsert keyed on `chunk.id`: re-running the job updates changed chunks instead of duplicating them — the foundation of incremental indexing.

### 8.6 Retrieval — Hybrid Search with Metadata Filtering

```python
# retrieval/vector_store.py  (Qdrant adapter, abridged)
from qdrant_client import QdrantClient, models
from domain.models import Chunk, RetrievedChunk
from domain.ports import VectorStore

class QdrantStore(VectorStore):
    def __init__(self, client: QdrantClient, collection: str):
        self.client, self.collection = client, collection

    def upsert(self, chunks, vectors):
        self.client.upsert(self.collection, points=[
            models.PointStruct(
                id=abs(hash(c.id)) % (2**63),
                vector={"dense": v},
                payload={
                    "chunk_id": c.id, "text": c.text,
                    "drug_names": c.drug_names, "content_type": c.content_type,
                    "population": c.population, "source_ref": c.source_ref,
                    "source_title": c.source_title,
                },
            ) for c, v in zip(chunks, vectors)
        ])

    def hybrid_search(self, query_text, query_vector, top_k, filters=None):
        # Build a metadata pre-filter (e.g. restrict to a drug and population).
        must = []
        if filters:
            if "drug" in filters:
                must.append(models.FieldCondition(
                    key="drug_names",
                    match=models.MatchValue(value=filters["drug"])))
            if "population" in filters:
                must.append(models.FieldCondition(
                    key="population",
                    match=models.MatchAny(any=filters["population"])))
        qfilter = models.Filter(must=must) if must else None

        # Qdrant runs dense + sparse and fuses with RRF server-side.
        results = self.client.query_points(
            self.collection, prefetch=[
                models.Prefetch(query=query_vector, using="dense",
                                filter=qfilter, limit=top_k * 4),
                models.Prefetch(query=models.Document(text=query_text, model="bm25"),
                                using="sparse", filter=qfilter, limit=top_k * 4),
            ],
            query=models.FusionQuery(fusion=models.Fusion.RRF),
            limit=top_k,
        ).points
        return [_to_retrieved(p) for p in results]
```

```python
# retrieval/query_transform.py — the multi-hop logic for interactions
import json
from domain.ports import LLM

DECOMPOSE_PROMPT = """Analyze this clinical question. Return JSON:
{{"is_interaction": bool, "drugs": [list of drug names],
  "population": [any of: adult, pediatric, pregnancy, renal_impairment, hepatic_impairment],
  "rewritten": "a clear standalone version of the question"}}
Question: {q}
Return ONLY JSON."""

def analyze_query(q: str, llm: LLM) -> dict:
    raw = llm.complete(system="You are a clinical query analyzer.",
                       user=DECOMPOSE_PROMPT.format(q=q))
    return json.loads(raw.strip().strip("```json").strip("```"))

def build_subqueries(analysis: dict) -> list[dict]:
    """An interaction question fans out into: one retrieval per drug
    PLUS one retrieval per drug-pair. This is query decomposition in action."""
    drugs = analysis["drugs"]
    pop = analysis.get("population", [])
    subs = [{"text": f"{d} dosing and safety", "filters": {"drug": d, "population": pop}}
            for d in drugs]
    if analysis["is_interaction"] and len(drugs) >= 2:
        for i in range(len(drugs)):
            for j in range(i + 1, len(drugs)):
                subs.append({
                    "text": f"interaction between {drugs[i]} and {drugs[j]}",
                    "filters": {"drug": drugs[i]},   # pair chunks carry both names
                })
    return subs
```

```python
# retrieval/retriever.py — ties it together
from domain.ports import Embedder, VectorStore, Reranker, LLM
from retrieval.query_transform import analyze_query, build_subqueries

class Retriever:
    def __init__(self, embedder: Embedder, store: VectorStore,
                 reranker: Reranker, llm: LLM):
        self.embedder, self.store = embedder, store
        self.reranker, self.llm = reranker, llm

    def retrieve(self, question: str, top_k: int = 6):
        analysis = analyze_query(question, self.llm)
        subqueries = build_subqueries(analysis) or [{"text": analysis["rewritten"],
                                                     "filters": None}]
        # Wide recall: gather candidates across all sub-queries, dedupe by chunk id.
        pool: dict[str, "RetrievedChunk"] = {}
        for sub in subqueries:
            qvec = self.embedder.embed_query(sub["text"])
            for rc in self.store.hybrid_search(sub["text"], qvec,
                                               top_k=20, filters=sub["filters"]):
                prev = pool.get(rc.chunk.id)
                if prev is None or rc.score > prev.score:
                    pool[rc.chunk.id] = rc
        # Precision: one rerank pass against the ORIGINAL question.
        reranked = self.reranker.rerank(analysis["rewritten"],
                                        list(pool.values()), top_k=top_k)
        return reranked, analysis
```

The two-stage shape is explicit here: fan out sub-queries and collect ~20 candidates each into a deduped pool (recall), then a single cross-encoder rerank against the original question trims to the best 6 (precision).

### 8.7 Generation — Grounding, Citations & Guardrails

```python
# generation/prompts.py
SYSTEM = """You are a clinical drug-information assistant for healthcare professionals.
Rules:
- Answer ONLY from the numbered sources. Never use outside knowledge.
- Cite every clinical claim inline as [n] matching the source numbers.
- If the sources are insufficient, state that clearly and do not speculate.
- For interactions, state severity, mechanism, and management if available.
- Always preserve exact doses, units, and frequencies verbatim from sources."""

def build_user_prompt(question: str, chunks) -> str:
    sources = "\n".join(
        f"[{i+1}] {rc.chunk.text}  (ref: {rc.chunk.source_ref})"
        for i, rc in enumerate(chunks)
    )
    return f"Sources:\n{sources}\n\nQuestion: {question}\n\nGrounded answer with [n] citations:"
```

```python
# generation/guardrails.py
import re
from domain.models import Answer, Citation

def verify_and_guard(raw_text: str, chunks) -> Answer:
    warnings, safe = [], True
    cited_nums = {int(n) for n in re.findall(r"\[(\d+)\]", raw_text)}

    # 1. Citation validity: every [n] must map to a real source.
    valid = set(range(1, len(chunks) + 1))
    if cited_nums - valid:
        warnings.append("Answer cited non-existent sources.")
        safe = False
    # 2. No-citation guard: a clinical answer with zero citations is untrustworthy.
    if not cited_nums and "insufficient" not in raw_text.lower():
        warnings.append("Answer made claims without citations.")
        safe = False
    # 3. Dose-safety guard: dosing statements should carry a caution.
    if re.search(r"\d+\s?(mg|mcg|g|ml)", raw_text) and \
       "healthcare professional" not in raw_text.lower():
        warnings.append("Dosing present without professional-judgment caveat.")

    citations = [
        Citation(ref=chunks[n-1].chunk.source_ref,
                 source_title=chunks[n-1].chunk.source_title,
                 chunk_id=chunks[n-1].chunk.id)
        for n in sorted(cited_nums) if n in valid
    ]
    return Answer(text=raw_text, citations=citations,
                  used_chunks=[c.chunk.id for c in chunks],
                  safe=safe, warnings=warnings)
```

```python
# generation/generator.py
from domain.ports import LLM
from generation.prompts import SYSTEM, build_user_prompt
from generation.guardrails import verify_and_guard

class Generator:
    def __init__(self, llm: LLM):
        self.llm = llm

    def generate(self, question: str, chunks):
        if not chunks:
            from domain.models import Answer
            return Answer(text="I don't have sources covering this question.",
                          citations=[], used_chunks=[], safe=True)
        raw = self.llm.complete(SYSTEM, build_user_prompt(question, chunks),
                                temperature=0.0)   # deterministic for clinical use
        return verify_and_guard(raw, chunks)
```

Temperature is pinned to 0 — in clinical retrieval you want reproducible, conservative output, not creative variation.

### 8.8 API Layer

```python
# api/main.py
from fastapi import FastAPI, Depends
from api.schemas import AskRequest, AskResponse
from retrieval.retriever import Retriever
from generation.generator import Generator

app = FastAPI(title="Clinical Drug Information Assistant")

def get_retriever() -> Retriever: ...   # wired at startup (DI)
def get_generator() -> Generator: ...

@app.post("/ask", response_model=AskResponse)
def ask(req: AskRequest,
        retriever: Retriever = Depends(get_retriever),
        generator: Generator = Depends(get_generator)):
    chunks, analysis = retriever.retrieve(req.question, top_k=req.top_k)
    answer = generator.generate(req.question, chunks)
    return AskResponse(
        answer=answer.text,
        citations=[c.__dict__ for c in answer.citations],
        safe=answer.safe,
        warnings=answer.warnings,
        detected_drugs=analysis.get("drugs", []),
        is_interaction_query=analysis.get("is_interaction", False),
    )

@app.get("/health")
def health():
    return {"status": "ok"}
```

```python
# api/schemas.py
from pydantic import BaseModel, Field

class AskRequest(BaseModel):
    question: str = Field(..., min_length=3)
    top_k: int = Field(6, ge=1, le=12)

class AskResponse(BaseModel):
    answer: str
    citations: list[dict]
    safe: bool
    warnings: list[str]
    detected_drugs: list[str]
    is_interaction_query: bool
```

### 8.9 Evaluation Harness

```python
# eval/run_eval.py
def recall_at_k(retrieved_ids: list[str], relevant_ids: set[str], k: int) -> float:
    hits = len(set(retrieved_ids[:k]) & relevant_ids)
    return hits / len(relevant_ids) if relevant_ids else 0.0

def mrr(retrieved_ids: list[str], relevant_ids: set[str]) -> float:
    for rank, cid in enumerate(retrieved_ids, start=1):
        if cid in relevant_ids:
            return 1.0 / rank
    return 0.0

def evaluate(testset, retriever):
    """testset: list of {question, relevant_chunk_ids}."""
    recalls, mrrs = [], []
    for case in testset:
        chunks, _ = retriever.retrieve(case["question"], top_k=6)
        ids = [c.chunk.id for c in chunks]
        rel = set(case["relevant_chunk_ids"])
        recalls.append(recall_at_k(ids, rel, k=6))
        mrrs.append(mrr(ids, rel))
    print(f"Recall@6: {sum(recalls)/len(recalls):.3f}  "
          f"MRR: {sum(mrrs)/len(mrrs):.3f}")

# Faithfulness (generation side) is scored separately with an LLM-as-judge:
FAITHFULNESS_JUDGE = """Given SOURCES and an ANSWER, is every claim in the ANSWER
supported by the SOURCES? Reply with a score 0-1 and list any unsupported claims.
SOURCES: {sources}
ANSWER: {answer}"""
```

Run `evaluate()` in CI on every change to the retrieval or chunking code — it's your regression suite. A drop in Recall@6 after a "harmless" chunking tweak is exactly the silent failure this catches.

### 8.10 How a Query Flows (worked example)

Query: *"Is it safe to give simvastatin to a patient already on clarithromycin?"*

1. **Analyze** → `{is_interaction: true, drugs: ["simvastatin","clarithromycin"], population: ["adult"], rewritten: "..."}`
2. **Decompose** → sub-queries: `[simvastatin dosing/safety]`, `[clarithromycin dosing/safety]`, `[interaction simvastatin+clarithromycin]`
3. **Hybrid retrieve** each (dense catches "safety/contraindication" semantics; BM25 nails the exact drug names) → ~60 candidates → deduped pool
4. **Rerank** against the original question → top 6, with the interaction chunk surfacing first
5. **Generate** grounded answer: *"This combination is contraindicated [1]. Clarithromycin strongly inhibits CYP3A4, raising simvastatin levels and myopathy/rhabdomyolysis risk [1][2]. Management: avoid co-administration; ..."*
6. **Guard**: citations valid ✓, present ✓ → `safe: true`, returned with sources.

Basic RAG would have embedded the whole question, likely retrieved general statin or macrolide chunks, and *missed the interaction entirely* — because no single chunk matches the full question well. The decomposition is what makes the multi-hop answer correct.


---

## 9. Common Failure Modes & Fixes

When a RAG system gives a bad answer, the trace (§7 observability) tells you *which stage* broke. This table maps symptoms to root causes and fixes — work it top to bottom.

| Symptom | Likely stage | Root cause | Fix |
|---|---|---|---|
| Answer invents facts | Retrieval | Relevant chunk never retrieved | Improve chunking, add hybrid/BM25, check embedding domain fit |
| Right topic, wrong details | Chunking | Chunks too large/small; context severed | Tune chunk size + overlap; parent-document retrieval |
| Misses exact terms (codes, doses) | Retrieval | Dense-only; no keyword match | Add sparse/BM25 → hybrid |
| Relevant chunk retrieved but ignored | Generation | Chunk buried mid-context | Rerank; put best chunks at prompt edges |
| Multi-part question half-answered | Query transform | No decomposition | Add query decomposition |
| Answer true but off-topic | Generation | Weak prompt / answer-relevance | Tighten instructions; measure answer relevance |
| Confident answer to unanswerable Q | Generation | No refusal path | Instruct "say I don't know"; short-circuit on empty retrieval |
| Slow responses | Whole pipeline | Serial LLM calls | Parallelize, cache, stream, skip stages for easy queries |
| Stale answers | Indexing | No incremental re-index | Version docs; re-embed only changes |
| Leaks unauthorized data | Retrieval | No access filter | Metadata pre-filter by caller identity |

The diagnostic principle: **retrieval failures and generation failures need opposite fixes.** If the right chunk wasn't retrieved, no prompt engineering saves you — fix retrieval. If it *was* retrieved but unused, retrieval is fine — fix the prompt or reranking. The evaluation split in §6 exists precisely to tell these apart.

---

## 10. Decision Cheat Sheet

**Do I even need RAG?**
- Knowledge fits in the prompt and rarely changes → just use long context.
- You need behavior/format/style, not facts → fine-tune.
- Large, changing, or private knowledge that must be cited → **RAG.**

**Chunking:** start recursive, ~400–800 tokens, ~15% overlap. Structured docs → structural chunking. Add contextual prefixes. Tune against evals.

**Retrieval:** default to **hybrid (dense + BM25 + RRF)**. Pure dense only if you have no exact-term needs (rare).

**Reranking:** almost always yes. Retrieve wide (~50–100), rerank, keep ~5. Biggest cheap quality win.

**Vector store:** starting out or already on Postgres → `pgvector`. Need scale + hybrid + filtering out of the box → Qdrant/Weaviate/Milvus. Want zero ops → managed (Pinecone).

**Advanced patterns:** add them *reactively*, driven by eval failures — decomposition for multi-hop, HyDE for vocabulary mismatch, parent-document for the chunk-size tension, agentic for genuinely multi-step questions. Don't build them speculatively.

**Evaluation:** build a 50-question golden set early. Measure retrieval (recall@k, MRR) and generation (faithfulness, answer relevance) *separately*. Run it in CI.

**Production:** cache aggressively, stream generation, pre-filter for access control, treat retrieved text as untrusted (prompt injection), log full traces, and design incremental indexing from day one.

---

### The one-paragraph summary

RAG is an open-book exam for LLMs: an **offline pipeline** turns your documents into a searchable index (load → chunk → embed → store), and an **online pipeline** answers questions by retrieving the most relevant chunks and forcing the model to answer only from them (transform → hybrid-retrieve → rerank → generate → guard). The craft is almost entirely in the retrieval half — chunking, hybrid search, and reranking decide whether the right evidence reaches the model — while grounding, citations, and guardrails decide whether you can trust what comes out. Measure the two halves separately, add complexity only when your evals demand it, and never let the model answer from anything it didn't retrieve.
