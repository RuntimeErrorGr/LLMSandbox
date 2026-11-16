# Step 1 — Platform basics and the first LangChain chain

## Web app

| File | Job |
|---|---|
| `app/config.py` | Settings from `.env` |
| `app/db.py`, `app/models.py` | SQLite via SQLAlchemy |
| `migrations/` | Alembic migrations (one per feature) |
| `app/health.py` | Status checks shown on the dashboard |
| `app/main.py` | Routes |
| `app/templates/` | Jinja pages + HTMX partials |

HTMX lets a part of the page reload itself from the server:

```mermaid
sequenceDiagram
    participant B as Browser (dashboard)
    participant F as FastAPI
    participant O as Ollama
    loop every 10s
        B->>F: GET /partials/status
        F->>O: GET /api/tags
        O-->>F: installed models
        F-->>B: <table> fragment, swapped into the page
    end
```

## LangChain in one picture

LangChain gives LLM building blocks that share one interface: `.invoke(input) -> output`.
They are connected with `|`, like Linux pipes.

```mermaid
flowchart LR
    In["{question, history}"] --> P[ChatPromptTemplate<br/>system + history + question]
    P --> L[ChatOllama<br/>qwen2.5-coder:7b]
    L --> S[StrOutputParser<br/>reply text only]
    S --> Out[answer string]
```

```python
chain = prompt | chat_model() | StrOutputParser()
answer = chain.invoke({"history": past_messages, "question": "What is label flipping?"})
```

The model has no memory of its own: the last 10 messages are loaded from the `chat_messages`
table and put into the prompt every time. That is why it "remembers".

## Chat request flow

```mermaid
sequenceDiagram
    participant B as Browser
    participant F as FastAPI /chat
    participant C as chain
    participant D as SQLite
    B->>F: POST question
    F->>D: load last 10 messages
    F->>C: invoke(history + question)
    C-->>F: answer
    F->>D: save question + answer
    F-->>B: two message bubbles (HTMX appends them)
```
