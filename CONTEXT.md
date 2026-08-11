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
A ranked, authorized Document Chunk with an RRF ordering score, raw keyword/vector relevance signals, retrieval method, and Citation.
_Avoid_: Generated answer, source document

**Citation**:
Stable source metadata containing Document title, Document Version, Section, and Chunk ID for one Search Result.
_Avoid_: URL, free-form source text

**Source Binding**:
The deterministic guarantee that every returned Citation is materialized from a Search Result admitted to the model Context. It does not prove that every answer sentence is entailed by that source.
_Avoid_: Groundedness proof, factuality score

**Relevance Policy**:
A version-sensitive rule that admits Search Results using calibrated raw keyword and vector signals before model generation. RRF score is never used as an answerability threshold.
_Avoid_: Rank cutoff, model confidence

**Model Gateway**:
The provider-neutral boundary for bounded structured generation, including model identity, Prompt version, timeout, attempts, and Token usage.
_Avoid_: Raw SDK client, Prompt text

**Grounded Answer**:
A validated RAG response produced under an evidence-only Prompt whose Citations are source-bound to current authorized Search Results. Sentence-level entailment still requires evaluation.
_Avoid_: Search Result, general model answer

**Conversation**:
A stable multi-turn identity with one fixed local role and an ordered sequence of user and assistant Messages.
_Avoid_: Agent Run, HTTP request

**Message**:
A persisted user question or assistant outcome. Assistant Messages own the retrieval query, retrieved Chunk IDs, model/Prompt/Token metadata, status, safe failure classification, latency, request ID, and optional final response JSON for one turn.
_Avoid_: Document Chunk, transient model message

**Turn Trace**:
The persisted succeeded, refused, or failed outcome of one accepted chat request. A failed trace has a stable error stage/code and no final answer response.
_Avoid_: Successful answer, Provider exception text

**Agent State**:
The checkpoint-safe, explicit state shared by LangGraph nodes for one Agent Run, including the request, user context, classification, evidence, plans, results, final response, error, retry count, and execution position.
_Avoid_: Prompt, Conversation history, hidden model reasoning

**Agent Run**:
One bounded LangGraph execution identified independently from a Conversation. It stores the latest recoverable Agent State, classification, lifecycle status, current node, request ID, and optional Conversation link.
_Avoid_: Conversation, HTTP request, successful answer

**Agent Step**:
One append-only attempt to execute a named graph node, with sequence, status, safe error code, state snapshot, and latency.
_Avoid_: Model token, tool audit, checkpoint internal row

**Tool Definition**:
The versioned allowlist contract for one tool, including strict input/output Schema, required permissions, risk, side-effect metadata, timeout, and finite retry policy.
_Avoid_: Function pointer, Prompt tool description

**Tool Observation**:
The bounded structured output or sanitized failure returned by ToolExecutionGateway and copied into Agent State for deterministic routing.
_Avoid_: Raw log, Adapter response body

**Tool Execution**:
One audited logical call through ToolExecutionGateway, including rejected and failed calls, linked to an optional Agent Run, actor, confirmation, and idempotency key.
_Avoid_: Agent Step, retry attempt, direct Adapter call

**Ticket**:
A local PostgreSQL IT support record created only by a confirmed R1 action, with requester, category, priority, status, diagnosis summary, idempotency key, and optional Conversation/Agent Run links.
_Avoid_: Pending Confirmation, external ServiceNow/Jira issue

**Pending Confirmation**:
A persisted, validated R1 action proposal awaiting confirmation from its original actor.
_Avoid_: Approval Request, Approval Decision, Executed Tool

**Local User**:
A locally provisioned demo identity whose active state, Roles, and Permissions are resolved before a governed action or approval decision.
_Avoid_: Trusted enterprise principal, self-reported role

**Role**:
A named bundle of Permissions assigned to Local Users for the simplified governance model.
_Avoid_: User type, request field

**Permission**:
A named authorization capability granted through a Role.
_Avoid_: Role, model recommendation

**Policy Decision**:
One deterministic outcome from allow, deny, require confirmation, require approval, or need more context for a fully described policy input.
_Avoid_: Model confidence, Approval Decision

**Approval Request**:
A persisted R3 authorization request with requester, target, business justification, source Agent Run, and current approval lifecycle.
_Avoid_: Pending Confirmation, Approval Decision

**Approval Decision**:
One immutable approve or reject judgment made by an authorized approver for an Approval Request.
_Avoid_: Policy Decision, user confirmation

**Simulated Execution**:
The local success outcome produced after approval without changing any real enterprise identity or permission system.
_Avoid_: Directory write, production access grant

**Audit Event**:
A sanitized, append-only policy or execution fact containing actor, action, target, parameter summary, policy decision, result, request ID, and timestamp.
_Avoid_: Full action payload, raw exception, Tool Observation

**Idempotency Key**:
A caller-supplied bounded key that binds one material write action and lets retries or duplicate confirmations return the original result without a second Ticket or Comment.
_Avoid_: Confirmation ID, request ID, Agent Run ID

**Reasoning Summary**:
A short model-supplied routing explanation constrained by Schema and length. It is not chain-of-thought and must not contain or claim to expose private model reasoning.
_Avoid_: Chain-of-thought, hidden reasoning, full deliberation

**Evaluation Dataset**:
A versioned, strictly validated collection of expected user context, intent, documents, tool calls, final status, prohibited actions, and reference answers with declared category counts.
_Avoid_: Ad-hoc demo prompts, production conversation dump

**Deterministic Evaluation Metric**:
A rule-owned calculation with an explicit denominator, such as Recall, Citation Validity, Tool Argument Accuracy, or Prohibited Action Rate. A missing applicable sample remains N/A rather than becoming zero.
_Avoid_: LLM preference score, subjective demo impression

**Evaluation Run**:
One complete dataset execution identified by dataset/corpus/code/workflow/model/Prompt versions, raw case observations, aggregates, gate result, and optional previous-run comparison.
_Avoid_: Agent Run, test-suite execution

**Advisory Judge**:
An optional model-based comparison recorded separately with provider, model, Prompt version, and Token usage. It is not ground truth and cannot override deterministic safety gates.
_Avoid_: Authorization decision, release gate truth

**Visibility**:
The retrieval access mode of a Document: public or role_restricted. A role_restricted Document is eligible only when the caller role is in allowed_roles.
_Avoid_: Authentication, ownership
