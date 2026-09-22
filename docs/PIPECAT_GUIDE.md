# Pipecat, explained through this project

This guide starts from zero. It explains what Pipecat is, how real-time voice
agents work, and how the LRN interview agent is put together.

## 1. What are we building?

The application is a browser-based interviewer. A candidate opens a web page,
allows microphone access, speaks, and hears an AI interviewer reply.

The conversation loop is:

```text
Candidate's voice
    -> WebRTC sends audio to Python
    -> Deepgram turns speech into text (STT)
    -> Groq creates an interview response (LLM)
    -> Deepgram turns text into speech (TTS)
    -> WebRTC sends audio back to the browser
    -> Candidate hears the reply
```

**Pipecat** is the framework coordinating this loop. It is not itself a speech
recognition company or an AI model. Instead, it provides the real-time plumbing
that lets providers such as Deepgram and Groq work together as one low-latency
voice application.

## 2. The words you will see in Pipecat

| Term | Plain-English meaning | In this app |
| --- | --- | --- |
| Frame | A small piece of information moving through the app. | Audio, a transcript, or a model response. |
| Processor | A component that accepts frames and emits new frames. | Deepgram STT, Groq, and Deepgram TTS. |
| Pipeline | An ordered chain of processors. | `microphone -> STT -> LLM -> TTS -> speakers`. |
| Transport | The input/output connection to a user. | `SmallWebRTCTransport` connects the browser. |
| Worker | The object that starts, owns, and stops one pipeline. | `PipelineWorker` owns one interview session. |
| Context | The running chat history and instructions sent to the LLM. | `LLMContext` remembers the interviewer prompt and turns. |
| STT | Speech-to-text. | Deepgram transcribes the candidate. |
| TTS | Text-to-speech. | Deepgram Aura speaks the interviewer response. |
| LLM | Large language model. | Groq's `openai/gpt-oss-20b` decides what to say. |
| WebRTC | The browser protocol for real-time audio/video/data. | Carries microphone and speaker audio. |

The useful mental model is a conveyor belt. Frames enter on the left, every
processor does one job, and frames leave on the right.

## 3. Why WebRTC?

Normal HTTP is ideal for requests such as “give me this web page.” Voice needs
continuous, two-way, low-latency audio while both people can interrupt each
other. WebRTC is built for that job.

For local development, Pipecat's `SmallWebRTCTransport` provides both:

1. a local signalling server that coordinates the connection, and
2. a prebuilt browser interface at `http://localhost:7860`.

The browser and Python process negotiate an audio connection using ICE. The
Google STUN server visible in the browser logs helps the peers discover network
addresses. For two devices on the public internet, a production app normally
also needs a TURN server because some networks block direct connections.

## 4. Project map

```text
lrn-interview-agent/
├── .env                         # Your local secret keys. Never commit this.
├── .env.example                 # Empty, safe template for the keys.
├── pyproject.toml               # Python version, packages, and command name.
├── README.md                    # Short setup guide.
├── docs/
│   └── PIPECAT_GUIDE.md         # This guide.
└── src/lrn_interview_agent/
    ├── __init__.py              # Makes this a Python package.
    └── bot.py                   # The actual voice agent.
```

Most of the application lives in `src/lrn_interview_agent/bot.py`.

## 5. Packages and credentials

`pyproject.toml` asks `uv` to install:

```toml
pipecat-ai[deepgram,groq,runner,webrtc]
```

The names in square brackets are **extras**: optional capabilities added to the
main Pipecat package.

| Extra | Why this project needs it |
| --- | --- |
| `deepgram` | Deepgram Python client for STT and TTS. |
| `groq` | Groq's OpenAI-compatible LLM client. |
| `runner` | Pipecat development server and its bundled browser client. |
| `webrtc` | Python WebRTC implementation used by the server. |

Your `.env` file contains:

```dotenv
DEEPGRAM_API_KEY=your_deepgram_key
GROQ_API_KEY=your_groq_key
```

`load_dotenv()` makes those values available to Python. `required_env()` checks
that a required key exists before a provider is created. It intentionally does
not print the key value.

## 6. The code, top to bottom

### 6.1 The interview instructions

`SYSTEM_PROMPT` is the agent's job description. It tells the model to be a
warm LRN interviewer, ask one question at a time, keep spoken replies short,
and avoid inventing hiring outcomes.

This is not Python control logic. It is natural-language guidance for the LLM.
Changing it changes the interviewer's behavior and tone, not the audio
connection.

### 6.2 `bot(runner_args)`

Pipecat's development runner finds and calls this async function whenever a
browser starts an interview session.

`runner_args` contains session-specific details. This project checks that it is
`SmallWebRTCRunnerArguments`, which prevents accidentally running this
WebRTC-only implementation through a different transport.

### 6.3 The transport

```python
transport = SmallWebRTCTransport(
    webrtc_connection=runner_args.webrtc_connection,
    params=TransportParams(audio_in_enabled=True, audio_out_enabled=True),
)
```

This object is the bridge between Pipecat and the browser.

- `transport.input()` emits microphone audio into the pipeline.
- `transport.output()` sends generated audio to the browser speakers.
- `audio_in_enabled=True` enables the candidate microphone.
- `audio_out_enabled=True` enables the agent's voice.

### 6.4 Conversation memory

```python
context = LLMContext(messages=[{"role": "system", "content": SYSTEM_PROMPT}])
aggregators = LLMContextAggregatorPair(context)
```

An LLM does not automatically remember earlier messages. The `LLMContext` holds
the instructions and chat history for this one session.

The pair of aggregators has two roles:

- `aggregators.user()` receives final Deepgram transcripts, adds the
  candidate's turn to the context, and triggers the LLM.
- `aggregators.assistant()` receives the agent's generated response and adds it
  to the context after it has been spoken.

Without these aggregators, the LLM would see no transcript or would lose the
conversation history after each question.

### 6.5 The providers

```python
DeepgramSTTService(...)  # Voice -> text
GroqLLMService(...)      # Text -> response text
DeepgramTTSService(...)  # Response text -> voice
```

The selected Groq model is `openai/gpt-oss-20b`. It replaced
`llama-3.1-8b-instant`, which Groq retired in August 2026. The model is called
through Groq's OpenAI-compatible API.

The selected voice is `aura-2-helena-en`. It is only a voice choice; it does
not affect the intelligence or interview instructions.

### 6.6 The pipeline itself

```python
Pipeline([
    transport.input(),
    DeepgramSTTService(...),
    aggregators.user(),
    GroqLLMService(...),
    DeepgramTTSService(...),
    transport.output(),
    aggregators.assistant(),
])
```

Read it left to right. This is the most important part of the project.

```text
Browser microphone
  -> SmallWebRTC input
  -> Deepgram STT
  -> user context aggregator
  -> Groq LLM
  -> Deepgram TTS
  -> SmallWebRTC output
  -> assistant context aggregator
```

The last aggregator is deliberately after audio output. It records what the
agent actually said, which keeps future answers consistent with the spoken
conversation.

### 6.7 The worker and lifecycle events

`PipelineWorker` wraps the pipeline and manages its lifecycle. Metrics are
enabled so Pipecat can report provider timing and usage information.

Two event handlers define the session behavior:

```python
@transport.event_handler("on_client_connected")
async def on_client_connected(...):
    await worker.queue_frames([LLMRunFrame()])
```

`LLMRunFrame` starts the first LLM generation. Because the context already
contains the interviewer prompt, the first response is the agent's spoken
introduction.

```python
@transport.event_handler("on_client_disconnected")
async def on_client_disconnected(...):
    await worker.cancel()
```

This stops provider connections and background work once the candidate leaves.
Without it, a disconnected call could leave a pipeline alive unnecessarily.

Finally, `WorkerRunner` starts the worker and waits until it finishes.

## 7. What happens during one answer?

Imagine the candidate says: “I built a Python API for an ecommerce app.”

1. Chrome captures microphone samples.
2. WebRTC streams those samples to `SmallWebRTCTransport`.
3. Deepgram emits interim transcript frames while the candidate speaks.
4. When Pipecat decides the turn is complete, Deepgram emits a final
   transcription frame.
5. The user aggregator appends that final text to `LLMContext`.
6. It sends the updated context to Groq.
7. Groq streams response text, perhaps: “What was the hardest scaling problem
   you solved in that API?”
8. Deepgram TTS converts that streamed text to audio frames.
9. The WebRTC output transport returns audio to Chrome.
10. The assistant aggregator stores the response in the conversation history.

Interim transcripts and duplicate-looking partial text in the browser debug
panel are normal. The final transcript is the turn that matters to the LLM.

## 8. Run it locally

From the project folder:

```powershell
uv sync
uv run lrn-interview-agent -t webrtc
```

Open the printed URL, normally `http://localhost:7860`, and grant microphone
permission. Keep the terminal open while testing.

To stop the server, focus that terminal and press `Ctrl+C`. Refreshing the
browser creates a new browser session, but does **not** reload Python code.
After changing `bot.py`, stop and start the server again.

## 9. Reading the logs

These log lines are useful checkpoints:

| Log message | Meaning |
| --- | --- |
| `GET /` then `GET /client/ 200 OK` | The Pipecat browser UI is installed and served. |
| `POST /start 200 OK` | Browser asked the runner to create a session. |
| `Peer connection established` | WebRTC connected successfully. |
| `Connecting to Deepgram` | Speech providers are starting. |
| `Pipeline ... ready` | Every processor is linked and ready. |
| `Generating chat from context` | A transcript or initial greeting triggered Groq. |
| `userTranscript` | Browser received an STT transcript. |
| `botReady` | Browser and Pipecat data channel are ready. |

### Common errors

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| `{"detail":"Not Found"}` at `/` | Runner browser extra was not installed. | Run `uv sync`; this project includes the `runner` extra. |
| `model_not_found` / HTTP 404 from Groq | Retired or inaccessible model ID. | Use the configured `openai/gpt-oss-20b` and restart the Python server. |
| HTTP 400 mentioning `reasoning_effort` | Unsupported parameter for the model/account. | Leave it unset, as this project does. |
| No transcript | Browser microphone permission, wrong selected mic, or Deepgram key issue. | Allow microphone access and check `DEEPGRAM_API_KEY`. |
| Transcript appears but no voice reply | Groq error, Deepgram TTS error, or speaker/output selection. | Read the terminal for the first `ERROR`; test the selected speaker. |
| It works locally but not from another network | WebRTC cannot establish a peer path. | Configure a production TURN server via Pipecat's `--ice-servers` option. |

## 10. Safe first changes to make

1. **Change the interview tone:** edit `SYSTEM_PROMPT`.
2. **Change the opening question:** add it to `SYSTEM_PROMPT`.
3. **Use another Deepgram voice:** change `aura-2-helena-en` in
   `DeepgramTTSService.Settings`.
4. **Collect candidate metadata:** pass a small `body` object when starting the
   session, then use `runner_args.body` to add role-specific instructions.
5. **Add a transcript UI:** use Pipecat's RTVI events in a custom frontend.

Do not put API keys in `bot.py`, the browser, screenshots, or Git commits.

## 11. What this project deliberately does not do yet

This is a focused, working voice interview loop. It does not yet persist
transcripts, authenticate candidates, score interviews, schedule calls, or
provide a branded custom web UI. Those are product features to add separately
once the core conversation is reliable.

## 12. Further reading

- [Pipecat documentation](https://docs.pipecat.ai/)
- [Pipecat development runner source](https://github.com/pipecat-ai/pipecat/blob/main/src/pipecat/runner/run.py)
- [Pipecat repository](https://github.com/pipecat-ai/pipecat)
- [Groq supported models](https://console.groq.com/docs/models)
- [Groq model deprecation notices](https://console.groq.com/docs/deprecations)
