# AI Career Coach for University Students

IS5542 · City University of Hong Kong

This is a one-page AI job-search workspace. A student brings a resume and a target job description (JD) and can then use three features in any order:

| Feature | What it does (follows M3 spec) |
|---|---|
| **Resume Optimization** (M3 p.1) | Shows each relevant resume line as **original → rewrite**, with the reason and the evidence ids behind it. The student can adopt, edit or keep each line. If a requirement has no evidence, the app asks the student to add material. It does not write the missing facts itself. |
| **Job Matching** (M3 p.2) | Takes the responsibilities, required items and preferred items from the JD. Each one is checked against resume quotes and labelled **Direct / Partial / No Evidence Found**. Each label comes with a next step (clarify / supplement / learn), and the items to handle first are listed. The result is not a hiring probability. |
| **Mock Interview** (M3 p.3) | Asks one question at a time, based on the JD and resume. Feedback covers only what the student actually said: on-topic quotes, missing information and one action to try next. The interviewer can ask a follow-up. The student can re-answer, take the follow-up, move to the next question, end the session or view a summary. Behavioral questions use STAR; technical questions look at method and reasoning. |

All three features use **one shared parse** of the materials (M3 p.4).

---

## Architecture

```
frontend/  React 18 + TypeScript + Vite + Tailwind CSS
backend/   Python FastAPI
  app/
    main.py        HTTP API, error mapping, serves frontend/dist in production
    materials.py   PDF text extraction, scanned-PDF detection, job-link import (SSRF-guarded),
                   deterministic segmentation into source lines (R1.., J1..)
    coach.py       shared bundle -> per-feature context -> LLM -> output verification
    grounding.py   checks numbers / tools / quantities in rewrites against cited evidence;
                   checks interview quotes against the actual answer
    kb.py          school-guidance knowledge base (BM25, English words + CJK bigrams)
    llm.py         OpenAI-compatible + Anthropic clients, JSON parsing with one repair retry
    config.py      env config + runtime override (memory only)
  prompts/         one prompt template per step; override in prompts/custom/
  data/kb/         drop guidance files here (.md / .txt / .pdf)
```

### Data flow (M3 page 4)

1. **Submit**: the resume comes from a PDF or pasted text. The JD is pasted or imported from a link.
2. **Readability check**: the app catches empty or too-short inputs, unreadable or encrypted PDFs, scanned PDFs with no text layer, unreachable or script-rendered job pages, and JDs with no recognisable requirements.
3. **Shared bundle**: both documents are split into addressable source lines (`R*` for the resume, `J*` for the JD). The model extracts requirements (`Q*`), and every requirement must cite a real `J*` line or it is dropped. Facts the student adds later become `S*` lines.
4. **Per-feature context**: student facts (`<resume_facts>`, `<student_supplements>`), job requirements (`<requirements>`) and school guidance (`<school_guidance>`, `G*`) go to the model in **separate blocks**. The rules say guidance is never evidence about the student.
5. **Output verification** (`coach.py`, `grounding.py`):
   - A rewrite that does not trace back to a real resume line is **not shown**. The UI reports how many were blocked.
   - Numbers, Chinese quantity words or tool/technology names that do not appear in the cited evidence mark the rewrite as **Needs verification**. It cannot then be adopted with one click; the student must edit it or keep the original.
   - A match item that cites evidence ids that do not exist is **downgraded** to "No evidence found".
   - An overview that contains probability or percentage language is suppressed.
   - Interview feedback quotes that do not appear in the student's answer are removed.
6. **Student decides**: adopt, edit or keep each rewrite; add evidence and regenerate; or keep practising.

When the materials change, results built from the old version are marked **stale** and cannot be acted on until the student re-analyzes.

---

## Running locally

Requirements: **Python 3.10+** and **Node 18+**.

### 1. Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # then fill in LLM_API_KEY / LLM_MODEL
uvicorn app.main:app --reload --port 8000
```

### 2. Frontend (dev)

```bash
cd frontend
npm install
npm run dev                 # http://localhost:5173 (proxies /api to :8000)
```

### Production (single process)

```bash
cd frontend && npm install && npm run build     # creates frontend/dist
cd ../backend && uvicorn app.main:app --port 8000
# open http://localhost:8000 — FastAPI serves the built frontend
```

On macOS/Linux, `./start.sh` does the production steps.

---

## Configuring the language model

The model and API key are **never hard-coded**. You can set them in two ways:

* **`backend/.env`** (recommended)
  ```ini
  LLM_PROVIDER=openai          # or anthropic
  LLM_API_KEY=sk-...
  LLM_MODEL=gpt-4o-mini        # any chat model id
  LLM_BASE_URL=                # optional: DeepSeek, Qwen-compatible, Azure gateway, local vLLM/Ollama…
  ```
* **Settings page** in the app: provider, model, base URL, key and timeout. The key is kept **only in backend process memory**. It is never written to disk, logs or the browser. Set `ALLOW_RUNTIME_CONFIG=false` to turn this off for shared deployments.

`provider=openai` works with any endpoint that speaks the OpenAI Chat Completions API. `provider=anthropic` uses the Claude Messages API.

Use **Settings → Test connection** to check the configuration.

> Without a key, the app still runs: the landing page, workspace, PDF/link import and settings all work. The AI features show a clear "model not configured" message. There are **no canned demo answers**.

---

## Knowledge base (RAG) and M3 prompts

* **Guidance files**: import M3 coaching guides (`.md` / `.txt` / `.pdf`) on the Settings page, or copy them into `backend/data/kb/`. Markdown headings become chunk sections. Retrieval is BM25 over English words and CJK bigrams. To switch to a vector store, re-implement `KnowledgeBase.search()` with the same return shape.
* **No knowledge base yet**: every result says that no school guidance is connected, and no guidance source is invented.
* **Prompts**: copy any file from `backend/prompts/` into `backend/prompts/custom/` with the same name and edit it. It takes effect on the next request. The placeholders `{{shared_rules}}` and `{{output_language}}` are filled in automatically.

API (selected): `GET /api/health`, `POST /api/materials/prepare`, `POST /api/resume/optimize`, `POST /api/match`, `POST /api/interview/{question,feedback,summary}`, `GET|POST|DELETE /api/kb…`, `POST /api/kb/search`.

---

## Languages

The interface is available in Simplified Chinese (default), Traditional Chinese (HK) and English. Every UI string is in `frontend/src/lib/i18n.ts`, and the dictionary types make a missing translation fail the build. Generated feedback is requested in the selected language. Resume rewrites stay in the **language of the original resume line**. The original resume and JD are never changed by a language switch. If a result was generated in another language, the app offers **Regenerate in current language**.

## Privacy and logging

* Logs contain only request paths and error codes. They never include resume text, JD text, answers or API keys.
* Materials, results and the interview history are saved in the browser (`localStorage`) so a refresh does not lose work. **Settings → Clear all local data** removes them.
* The job-link import refuses private, loopback and link-local hosts.

## Verification status

* The full UI flow was tested end-to-end in Chromium at **1440×900** and **1280×800**: landing, workspace, all three features, language switching, stale-result detection and error states. There were no console errors and no horizontal overflow.
* That test used a **local stub endpoint that mimics the OpenAI API**, with deliberately bad outputs to exercise the verification layer. It was not a real model. The stub is **not** part of this project.
* **Not yet verified:** output quality with a real LLM provider, because no API key was available while building. Run *Settings → Test connection* with your key, then try the sample materials.
* Out of scope by design: user accounts, payments, multi-project management.
