# LRN AI Voice Interview Agent

## 1. Project Goal

Build a small, working LRN voice-interview prototype first. A candidate joins a browser interview, the LRN interviewer speaks first, listens to answers, progresses through a bounded interview, and eventually returns learning recommendations. This is a focused voice module, not a rewrite of the wider LRN product.

## 2. Current Architecture

```text
Candidate microphone
  -> SmallWebRTC input -> Deepgram STT -> user context aggregator
  -> Groq LLM -> Deepgram TTS -> SmallWebRTC output
  -> Candidate speaker

Assistant context aggregator stores the spoken LLM reply.
```

## 3. Technology Stack

| Concern | Choice |
| --- | --- |
| Runtime / packages | Python 3.13.2, uv |
| Voice orchestration | Pipecat 1.11.0 |
| Browser transport | SmallWebRTC |
| STT / TTS | Deepgram |
| LLM | Groq (`openai/gpt-oss-20b`) |
| Durable storage | PostgreSQL, to be connected after `DATABASE_URL` is configured |

Credentials stay in `.env`; `.env.example` contains only variable names.

## 4. Pipecat Concepts

**Concept: Frame**

What: A small audio, text, or control event moving through Pipecat.

Why: One model can carry microphone audio, transcriptions, LLM requests, speech, and interruptions.

In our project: `LLMRunFrame` starts an interviewer response.

**Concept: Processor**

What: A focused pipeline stage that receives and emits frames.

Why: STT, LLM, and TTS each have one responsibility.

In our project: Deepgram STT transcribes, Groq generates interviewer text, and Deepgram TTS speaks it.

**Concept: PipelineWorker**

What: Pipecat 1.11's runtime for a pipeline.

Why: It runs frames, metrics, cancellation, and a single interview session.

In our project: each connected browser gets one worker.

**Concept: WorkerRunner**

What: The manager for one or more workers.

Why: It owns service-level lifecycle and replaces older tutorial APIs such as `PipelineTask` / `PipelineRunner`.

In our project: it starts the worker and stops it on browser disconnect.

## 5. Architecture Diagram

```text
Browser                         Pipecat service                         AI services
-------                         ---------------                         -----------
mic -> SmallWebRTC input -> Deepgram STT -> user context -> Groq LLM
speaker <- SmallWebRTC output <- Deepgram TTS <- assistant context <- /
```

## 6. Implementation Roadmap

| Phase | Outcome | Status |
| --- | --- | --- |
| 0 | Audit project and version-specific APIs | Complete |
| 1 | Stable voice pipeline | In progress; existing path manually validated |
| 2 | AI speaks first | Implemented; browser verification next |
| 3 | Conversation context | Baseline implemented |
| 4 | Deterministic interview state | Baseline implemented |
| 5 | Interviewer persona / prompt layers | Implemented for IB prototype |
| 6 | Bounded questions | Implemented; adaptive follow-up is next refinement |
| 7 | Barge-in verification | Planned |
| 8 | Custom LRN interview UI | Implemented for local prototype |
| 9 | Frontend/session architecture | Implemented for local prototype |
| 10 | Structured transcript storage | Planned |
| 11 | Evaluation report | Planned |
| 12 | Learning recommendations | Planned |
| 13 | Graceful errors | Planned |
| 14 | Production-readiness review | Planned |

## 7. Phase-by-Phase Implementation Notes

### Phase 0 — Audit Existing Project

#### What we did

Reviewed `bot.py`, `pyproject.toml`, `uv.lock`, `.env` conventions, the current runner and browser logs. Read current official Pipecat documentation and matched it to the installed Pipecat 1.11.0 dependency.

#### Why we did it

The basic transport already connects. Preserving working code reduces risk and avoids copying deprecated Pipecat examples.

#### How we did it

The entry point is `src/lrn_interview_agent/bot.py` and runs with:

```powershell
uv run lrn-interview-agent -t webrtc
```

It receives `SmallWebRTCRunnerArguments`, constructs `SmallWebRTCTransport`, then runs a `PipelineWorker` through `WorkerRunner`.

#### What is happening internally

```text
Browser connects to /api/offer
  -> SmallWebRTC emits on_client_connected
  -> Pipecat worker runs processors in order
  -> media and control frames move through the pipeline
```

#### Important concepts

- Runner arguments
- SmallWebRTC transport
- Pipeline
- PipelineWorker
- WorkerRunner
- Environment variables

#### Files changed

- `PIPECAT_BUILD_NOTES.md`

#### How to test

```powershell
uv sync
uv run lrn-interview-agent -t webrtc
```

#### Expected result

The local server starts without exposing any key. The browser can request microphone permission and establish WebRTC.

#### Common errors

- `{"detail":"Not Found"}`: the runner/prebuilt client dependency is missing, the wrong URL is opened, or an old server is still running.
- `UnicodeEncodeError: 'charmap' codec can't encode ...` before the server starts: a Windows terminal is using cp1252 while Pipecat prints a Unicode runner banner. `run()` reconfigures standard output/error to UTF-8 before invoking the runner.
- Windows `WinError 10048` on port 7860: another local runner already owns that port. Stop the old server before starting this checkout, or choose a different runner port.
- Groq `404 model`: the selected model is retired or unavailable. This project uses the live-checked `openai/gpt-oss-20b`.
- `reasoning_effort` `400`: an unsupported model parameter was sent to Groq. It was removed.

#### Decisions / trade-offs

SmallWebRTC remains the local prototype transport because it is the working P2P base. A production global deployment may need Daily and TURN infrastructure; that is a later deployment decision, not a reason to replace the prototype now.

### Phase 1 — Stable Voice Pipeline

#### What we did

Retained the existing SmallWebRTC -> Deepgram STT -> Groq -> Deepgram TTS -> SmallWebRTC flow, and changed the retired Llama model to `openai/gpt-oss-20b`.

#### Why we did it

The interviewer cannot function until candidate speech is transcribed, sent to the LLM, converted to audio, and played back.

#### How we did it

`bot.py` builds this processor order:

```python
[transport.input(), stt, user_aggregator, llm, tts, transport.output(), assistant_aggregator]
```

#### What is happening internally

```text
AudioFrame -> Deepgram STT -> TranscriptionFrame -> user context
           -> Groq -> TTSTextFrame -> Deepgram TTS -> AudioFrame
```

#### Important concepts

- Input/output transport processors
- STT
- LLM
- TTS
- Context aggregator

#### Files changed

- `src/lrn_interview_agent/bot.py`
- `pyproject.toml`
- `uv.lock`
- `.env.example`
- `README.md`
- `docs/PIPECAT_GUIDE.md`

#### How to test

```powershell
uv sync
uv run lrn-interview-agent -t webrtc
```

Connect, allow microphone access, say a sentence, and verify a spoken reply.

#### Expected result

The browser reaches `ready`, user transcripts appear, and the candidate hears a response.

#### Common errors

- No transcript: check browser microphone permission and `DEEPGRAM_API_KEY`.
- No reply: check `GROQ_API_KEY`, the configured model, and server logs.
- No sound: check browser/tab audio output and Deepgram credentials.

#### Decisions / trade-offs

Deepgram remains both STT and TTS because it is already configured and keeps the prototype small. We do not add another provider or VAD dependency unless a tested need appears.

### Phase 2 — AI Speaks First

#### What we did

On `on_client_connected`, the service writes a one-time startup developer message into context and queues `LLMRunFrame`.

#### Why we did it

An interview must be initiated by the interviewer; waiting for candidate audio creates a generic voice-chat experience.

#### How we did it

Pipecat 1.11 puts durable persona instructions in `GroqLLMService.Settings(system_instruction=...)`. `LLMContext()` begins empty. When the browser connects, `START_INTERVIEW_INSTRUCTION` explains that the candidate joined, then `LLMRunFrame` starts an LLM turn.

#### What is happening internally

```text
on_client_connected
  -> add startup developer message to LLMContext
  -> queue LLMRunFrame
  -> Groq generates opening text
  -> Deepgram TTS speaks it
  -> assistant aggregator retains the spoken opening
```

#### Important concepts

- `on_client_connected`
- `LLMRunFrame`
- `system_instruction`
- Developer message
- Initial bot turn

#### Files changed

- `src/lrn_interview_agent/bot.py`
- `PIPECAT_BUILD_NOTES.md`

#### How to test

```powershell
uv run lrn-interview-agent -t webrtc
```

Connect and remain silent. The interviewer should greet the candidate and ask for an introduction.

#### Expected result

The first voice heard is the LRN interviewer. The opening is recorded in conversation context after it is spoken.

#### Common errors

- Connected but silent: confirm the connection handler runs and queues one `LLMRunFrame` after worker creation.
- Opening twice: inspect for two independent browser WebRTC connections.

#### Decisions / trade-offs

The opening uses Pipecat events and frames, not `sleep`, manual playback, or a browser-side clip. It therefore follows the same LLM/TTS/context path as later interviewer replies.

### Phase 3 — Conversation Context (baseline)

#### What we did

Added `LLMContextAggregatorPair` around the LLM.

#### Why we did it

The agent must remember candidate answers and previous questions so it can ask relevant follow-ups.

#### How we did it

The user aggregator sits before the LLM; the assistant aggregator sits after output. Both update the same `LLMContext` across one session.

#### What is happening internally

```text
Candidate: "I built a FastAPI backend."
  -> user aggregator adds it to context
  -> next LLM turn can use that fact
  -> assistant aggregator adds the question actually spoken
```

#### Important concepts

- `LLMContext`
- `LLMContextAggregatorPair`
- User turn
- Assistant turn

#### Files changed

- `src/lrn_interview_agent/bot.py`
- `PIPECAT_BUILD_NOTES.md`

#### How to test

Mention a project, then ask the interviewer what project you mentioned. It should retain the detail during that WebRTC session.

#### Expected result

Later questions can relate to earlier answers. Question limits and records are intentionally not left to LLM memory; those arrive in Phase 4.

#### Decisions / trade-offs

Conversation context stores natural dialogue. It is not an authoritative source for deterministic question counts, session status, or persistent database rows.

## 8. Interview State Architecture

### Phase 4 — Deterministic Interview State (baseline)

#### What we did

Created `InterviewState`, an in-memory per-session state object, and connected Pipecat's finalized user/assistant turn events to its transcript. The state has a session ID, mode, status, stage, question limit, questions, answers, topics, and a transcript.

#### Why we did it

The LLM is good at natural conversation but is not a reliable database or counter. The application must own deterministic facts: whether the interview is active, how many scored questions are allowed, and what was actually said.

#### How we did it

`InterviewState.add_question()` is the only method that advances the scored question number. It refuses to go above `max_questions`. `on_user_turn_stopped` stores finalized candidate text, while `on_assistant_turn_stopped` stores the assistant text that was actually spoken (including interruption information). A unit test verifies the limit and transcript behavior.

#### What is happening internally

```text
Pipecat final user turn -> InterviewState.record_candidate_turn()
Pipecat completed/interrupted assistant turn -> InterviewState.record_interviewer_turn()
Future question planner -> InterviewState.add_question()
```

#### Important concepts

- Application state vs. LLM context
- Finalized turn events
- Session ID
- State machine
- Transcript entry

#### Files changed

- `src/lrn_interview_agent/interview_state.py`
- `src/lrn_interview_agent/bot.py`
- `tests/test_interview_state.py`
- `PIPECAT_BUILD_NOTES.md`

#### How to test

```powershell
uv run python -m unittest discover -s tests -v
uv run python -m compileall -q src
```

#### Expected result

The test passes. A session can retain finalized speaker turns and cannot register more than its configured maximum number of scored questions.

#### Common errors

- Attempting to add a question before a session is active raises `Cannot add a question to an inactive interview.`
- Attempting to add beyond the configured limit raises `The interview has reached its question limit.`

#### Decisions / trade-offs

The first version remains in memory so it has no mandatory database service and is easy to test. It is intentionally not durable across process restarts. PostgreSQL persistence will be added behind this state model, rather than making the LLM or browser the source of truth.

### State shape

```python
{
    "session_id": "...",
    "mode": "investment_banking_technical",
    "stage": "introduction",
    "question_number": 0,
    "max_questions": 6,
    "questions": [],
    "answers": [],
    "topics": [],
    "status": "active",
}
```

The application enforces count and completion. The LLM handles natural phrasing, follow-ups, and difficulty within that bound.

## 9. LLM Prompt Architecture

```text
System instruction: enduring LRN interviewer rules
Developer state message: mode, stage, limit, and topic
Conversation context: real exchanged questions and answers
Candidate turn: current answer
```

### Phase 5–6 — Interview Persona and Bounded Question Plan

#### What we did

Changed the persona to an LRN finance and investment-banking interviewer. Added a six-question investment-banking technical plan and made application state select the next scored question.

#### Why we did it

The interview must feel structured and must end. A general conversational prompt cannot guarantee that six relevant questions are asked or that the session stops at six.

#### How we did it

`question_plan.py` holds the small prototype bank. On connection, the app registers question one in `InterviewState`; after each final candidate turn, it registers the next question. The system adds a developer instruction containing the exact question and one-based question number. When the final answer arrives, it adds an instruction to close the session without another question.

#### What is happening internally

```text
Browser connects -> app selects question 1 -> LLM speaks it
Candidate final turn -> app records answer -> app selects question 2 -> LLM replies
Final answer -> app marks state complete -> LLM gives a short close
```

#### Important concepts

- System instruction
- Developer instruction
- Curated question plan
- Bounded interview
- State-owned progression

#### Files changed

- `src/lrn_interview_agent/question_plan.py`
- `src/lrn_interview_agent/bot.py`
- `tests/test_interview_state.py`
- `PIPECAT_BUILD_NOTES.md`

#### How to test

```powershell
uv run python -m unittest discover -s tests -v
uv run lrn-interview-agent -t webrtc
```

Join the interview and answer each question. The first is an introduction; after six final answers, the assistant should close instead of asking question seven.

#### Expected result

The interview has a concrete IB structure and no longer relies on the LLM to count or choose every topic.

#### Decisions / trade-offs

The first working prototype uses a curated six-question plan rather than dynamic generation. It is predictable, easy to test, and matches the requested small scope. A later planner can generate variants by domain but must still write them into this same bounded state before they are asked.

#### Interview acknowledgement refinement

The next-question instruction now requires the interviewer to acknowledge one concrete detail from the immediately previous candidate answer before asking question 2–6. For example, after a candidate mentions building a DCF, the interviewer can say, “You mentioned building a DCF for a consumer business,” then ask the accounting question. This makes the turn feel heard without turning the interviewer into a coach, scoring engine, or long summarizer.

The rule is implemented in `question_turn_instruction()` and is exercised by a unit test. A synthetic live Groq check also returned this acknowledgement pattern before its next question.

### Verification snapshot — 2026-09-22

| Check | Result |
| --- | --- |
| Python unit tests | Passed: state limit, question-plan bounds, acknowledgement instruction |
| Python compilation | Passed |
| Next.js production build | Passed |
| Pipecat client route (`/client/`) | HTTP 200 |
| WebRTC CORS preflight (`/api/offer`) | HTTP 200 from `http://localhost:3000` |
| Custom UI WebRTC smoke test | Passed: connecting -> listening, microphone connected, timer running |
| Synthetic Groq acknowledgement turn | Passed with `openai/gpt-oss-20b` |

Not fully automatable locally: microphone permissions, actual speaker output, network-quality degradation, and third-party provider outages. The UI now turns unreachable-backend and provider errors into visible session messages rather than silently leaving the candidate at “Connecting.”

## 10. Voice Pipeline

See the diagram above. Pipecat's normal context/user-turn handling supports interruption frames. Phase 7 will verify real barge-in in the browser before making a stronger claim.

## 11. Frontend Architecture

### Phase 8–9 — Custom LRN Interface and Browser Connection

#### What we did

Created a small Next.js client in `web/`. It presents an LRN investment-banking interview room with a start/end control, timer, connection state, microphone state, and six-step interview rail. It uses Pipecat's official browser SDK packages rather than the prebuilt development UI.

#### Why we did it

The prebuilt client proves the voice service works but does not communicate the LRN interview structure. The product UI should make the candidate feel they entered a focused interview session, not a generic bot sandbox.

#### How we did it

`PipecatClient` comes from `@pipecat-ai/client-js`; React bindings, `PipecatClientAudio`, and the transport-state hook come from `@pipecat-ai/client-react`. `SmallWebRTCTransport` is configured at click time with the Python server's offer endpoint:

```js
client.connect({
  webrtcRequestParams: { endpoint: "http://localhost:7860/api/offer" },
});
```

The WebRTC client is created inside `useEffect`, not during Next.js prerendering, because browser WebRTC APIs do not exist on the server.

#### What is happening internally

```text
Candidate clicks Begin interview
  -> browser asks for microphone permission
  -> Pipecat browser client POSTs WebRTC offer to :7860/api/offer
  -> Python runner creates a Pipecat worker
  -> worker queues the opening LLM turn
  -> remote audio is rendered by PipecatClientAudio
```

#### Important concepts

- Pipecat browser client
- SmallWebRTC browser transport
- Offer endpoint
- Browser-only WebRTC initialization
- Transport state

#### Files changed

- `web/package.json`
- `web/package-lock.json`
- `web/app/layout.js`
- `web/app/page.js`
- `web/app/globals.css`
- `README.md`
- `.gitignore`
- `PIPECAT_BUILD_NOTES.md`

#### How to test

Terminal 1:

```powershell
uv run lrn-interview-agent -t webrtc
```

Terminal 2:

```powershell
cd web
npm install
npm run dev
```

Open `http://localhost:3000`, click **Begin interview**, grant microphone permission, then remain silent for the opening.

#### Expected result

The UI changes from ready to connecting/ready, the timer starts, and the LRN interviewer opens the conversation through the normal Pipecat voice pipeline.

#### Common errors

- `WebRTC not supported or suppressed` during `next build`: browser-only WebRTC was constructed during prerendering. Create the client in `useEffect`.
- `Export PipecatClient doesn't exist`: the current React package exports UI bindings only. Import `PipecatClient` from `@pipecat-ai/client-js` and use `usePipecatClientTransportState` from the React package.
- Browser cannot connect: confirm the Python server is running on port 7860 and that `http://localhost:7860/api/offer` is reachable.

#### Decisions / trade-offs

The UI is a separate local Next.js process for a clean frontend/backend boundary. Pipecat's runner currently permits cross-origin development requests. Production should replace the hardcoded local endpoint with an environment variable and serve both applications behind HTTPS.

The question rail is intentionally a six-question prototype display. Real-time question numbers and transcript/report views will be supplied by the session API and PostgreSQL persistence phase, so business logic is not duplicated in the browser.

The frontend shows a visible connection failure if the backend offer endpoint is unavailable. `NEXT_PUBLIC_PIPECAT_URL` defaults to `http://localhost:7860` for local development and can be overridden in `web/.env.local` for a deployed backend.

## 12. Backend Architecture

```text
Custom browser UI -> SmallWebRTC /api/offer -> Pipecat session
                                               -> Deepgram / Groq
                                               -> PostgreSQL transcript/results
```

Pipecat owns live voice and authoritative session state. The frontend renders state and controls. PostgreSQL owns durable records.

## 13. Data Flow

Planned saved data: session metadata, question plan, question/answer entries, evaluation JSON, and LRN recommendations. Store structured evidence, never hidden model reasoning.

## 14. Error Handling

Later phases will convert provider, network, microphone, empty-transcript, timeout, and disconnect failures into safe session events and friendly UI states instead of raw exceptions.

## 15. Production Considerations

Prototype: local SmallWebRTC, `.env`, one process, optional PostgreSQL.

Production: HTTPS, TURN, isolated sessions, secret manager, structured logs/metrics, health checks, timeouts, rate limits, migrations, access control, and cost limits.

## 16. Things I Learned

- Pipecat 1.11 uses `PipelineWorker` and `WorkerRunner`.
- `LLMRunFrame` is the supported way to start a normal LLM response.
- `system_instruction` holds durable role rules; context holds actual conversation.
- Context memory and deterministic application state solve different problems.

## 17. Open Questions

- Which LRN auth source supplies candidate identity?
- Which hosted PostgreSQL instance will provide `DATABASE_URL`?
- Which existing LRN design tokens should the standalone prototype inherit?

## 18. Future Improvements

- Finance/IB domain question plans with LLM-generated variants
- Post-interview rubric evaluation
- Weak-topic lesson mapping
- Authenticated session creation
- Daily/TURN deployment for production
