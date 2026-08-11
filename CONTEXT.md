# Enterprise IT Support Knowledge Context

This glossary defines the knowledge-ingestion language used by the Enterprise IT Support AI Agent. It distinguishes stable document identity from immutable imported content and retrievable text units.

## Language

**Knowledge Source**:
A named collection or origin that owns related enterprise knowledge documents, such as a local IT handbook upload collection.
_Avoid_: File type, folder path

**Document**:
A stable logical knowledge item identified within one Knowledge Source by its title, regardless of how many times its content changes.
_Avoid_: File, upload, version

**Document Version**:
An immutable snapshot of a Document's normalized content created only when that content changes.
_Avoid_: Revision row, current document

**Document Chunk**:
An ordered, traceable portion of one Document Version that preserves enough source position information to locate its original section, paragraph, line, or page.
_Avoid_: Embedding, vector

**Document Content**:
The format-independent parsed representation made of titled or untitled sections before persistence and chunking.
_Avoid_: Raw file, chunk list

**Duplicate Import**:
An import whose normalized content hash already exists for the same Document and therefore reuses the existing Document Version.
_Avoid_: Duplicate document

**Embedding**:
A numeric representation of a Document Chunk generated under one Embedding Profile and comparable only with vectors from the same profile.
_Avoid_: Chunk, vector index

**Embedding Profile**:
The model name, output dimension, and application-controlled version that identify one compatible embedding space.
_Avoid_: Model name, provider configuration

**Indexed Chunk**:
A Document Chunk whose Embedding and complete Embedding Profile metadata were saved successfully at a known time.
_Avoid_: Imported chunk, searchable document

**Knowledge Retrieval**:
The deterministic boundary that applies document validity and role authorization before ranking keyword and vector Chunk candidates.
_Avoid_: RAG answer, chat response

**Search Result**:
A ranked, authorized Document Chunk with a fused score, retrieval method, and Citation.
_Avoid_: Generated answer, source document

**Citation**:
Stable source metadata containing Document title, Document Version, Section, and Chunk ID for one Search Result.
_Avoid_: URL, free-form source text

**Model Gateway**:
The provider-neutral boundary for bounded structured generation, including model identity, Prompt version, timeout, attempts, and Token usage.
_Avoid_: Raw SDK client, Prompt text

**Grounded Answer**:
A validated RAG response whose claims are constrained by the supplied enterprise Context and whose Citations are materialized from current authorized Search Results.
_Avoid_: Search Result, general model answer

**Conversation**:
A stable multi-turn identity with one fixed local role and an ordered sequence of user and assistant Messages.
_Avoid_: Agent Run, HTTP request

**Message**:
A persisted user question or assistant answer. Assistant Messages own the retrieval query, retrieved Chunk IDs, model/Prompt/Token metadata, latency, request ID, and final response JSON for one turn.
_Avoid_: Document Chunk, transient model message

**Visibility**:
The retrieval access mode of a Document: public or role_restricted. A role_restricted Document is eligible only when the caller role is in allowed_roles.
_Avoid_: Authentication, ownership
