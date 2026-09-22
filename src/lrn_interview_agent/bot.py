"""LRN's browser-based voice interview agent."""

import os

from dotenv import load_dotenv
from pipecat.frames.frames import LLMRunFrame
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.worker import PipelineParams, PipelineWorker
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import LLMContextAggregatorPair
from pipecat.runner.run import main
from pipecat.runner.types import RunnerArguments, SmallWebRTCRunnerArguments
from pipecat.services.deepgram.stt import DeepgramSTTService
from pipecat.services.deepgram.tts import DeepgramTTSService
from pipecat.services.groq.llm import GroqLLMService
from pipecat.transports.base_transport import TransportParams
from pipecat.transports.smallwebrtc.transport import SmallWebRTCTransport
from pipecat.workers.runner import WorkerRunner

from lrn_interview_agent.interview_state import InterviewState
from lrn_interview_agent.question_plan import InterviewQuestion, build_question_plan


load_dotenv(override=True)

SYSTEM_PROMPT = """
You are LRN's warm, concise voice interviewer for finance and investment
banking practice. Start by introducing yourself and asking the candidate to
introduce themselves. Then ask one focused question at a time, adapting a
follow-up only when it helps assess their answer. Cover finance fundamentals,
valuation, accounting, markets, problem solving, and communication as suitable
for the interview. Keep every spoken reply under two short sentences. Do not
use markdown, lists, emojis, or say that you are an AI. Never invent hiring
outcomes, company policy, or personal information. Do not reveal internal
evaluation. At the end, thank the candidate and say that their practice report
is ready to review.
""".strip()

START_INTERVIEW_INSTRUCTION = """
The candidate has joined the interview. Start now: briefly introduce yourself
as the LRN interviewer, welcome the candidate, and ask them to introduce
themselves. This is the first spoken response, so do not wait for the
candidate to speak first.
""".strip()


def required_env(name: str) -> str:
    """Return a required credential without ever logging its value."""
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"{name} is required. Add it to .env before starting the agent.")
    return value


async def bot(runner_args: RunnerArguments) -> None:
    """Create and run one WebRTC interview session."""
    if not isinstance(runner_args, SmallWebRTCRunnerArguments):
        raise ValueError("This agent currently supports the WebRTC transport only.")

    transport = SmallWebRTCTransport(
        webrtc_connection=runner_args.webrtc_connection,
        params=TransportParams(audio_in_enabled=True, audio_out_enabled=True),
    )
    # Pipecat 1.11 keeps durable system instructions on the LLM service. The
    # context itself stores the conversation that actually occurs.
    context = LLMContext()
    aggregators = LLMContextAggregatorPair(context)
    interview_state = InterviewState()
    question_plan = build_question_plan(interview_state.mode, interview_state.max_questions)

    def queue_question_instruction(question: InterviewQuestion) -> None:
        question_number = interview_state.add_question(question.prompt, question.topic)
        context.add_message(
            {
                "role": "developer",
                "content": (
                    f"This is scored question {question_number} of "
                    f"{interview_state.max_questions}. Ask this question naturally "
                    f"and concisely, without changing its meaning: {question.prompt}"
                ),
            }
        )
    worker = PipelineWorker(
        Pipeline(
            [
                transport.input(),
                DeepgramSTTService(api_key=required_env("DEEPGRAM_API_KEY")),
                aggregators.user(),
                GroqLLMService(
                    api_key=required_env("GROQ_API_KEY"),
                    settings=GroqLLMService.Settings(
                        model="openai/gpt-oss-20b",
                        system_instruction=SYSTEM_PROMPT,
                    ),
                ),
                DeepgramTTSService(
                    api_key=required_env("DEEPGRAM_API_KEY"),
                    settings=DeepgramTTSService.Settings(voice="aura-2-helena-en"),
                ),
                transport.output(),
                aggregators.assistant(),
            ]
        ),
        params=PipelineParams(enable_metrics=True, enable_usage_metrics=True),
    )

    @transport.event_handler("on_client_connected")
    async def on_client_connected(transport, client) -> None:
        # This supported P2P startup path puts the opening in the same
        # LLM/TTS/context pipeline as every later interviewer turn.
        interview_state.start()
        queue_question_instruction(question_plan[0])
        context.add_message(
            {
                "role": "developer",
                "content": f"{START_INTERVIEW_INSTRUCTION} Ask the first scored question now.",
            }
        )
        await worker.queue_frames([LLMRunFrame()])

    @aggregators.user().event_handler("on_user_turn_stopped")
    async def on_user_turn_stopped(aggregator, strategy, message) -> None:
        interview_state.record_candidate_turn(message.content, message.timestamp)
        if not message.content or interview_state.status.value != "active":
            return

        if interview_state.question_number >= interview_state.max_questions:
            interview_state.complete()
            context.add_message(
                {
                    "role": "developer",
                    "content": "The candidate answered the final question. Thank them warmly, say their practice report will be ready shortly, and end the interview. Do not ask another question.",
                }
            )
            return

        queue_question_instruction(question_plan[interview_state.question_number])

    @aggregators.assistant().event_handler("on_assistant_turn_stopped")
    async def on_assistant_turn_stopped(aggregator, message) -> None:
        interview_state.record_interviewer_turn(
            message.content, message.timestamp, message.interrupted
        )

    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, client) -> None:
        interview_state.cancel()
        await worker.cancel()

    runner = WorkerRunner(handle_sigint=runner_args.handle_sigint)
    await runner.add_workers(worker)
    await runner.run()


def run() -> None:
    """Expose the agent through the installed command as well as ``python -m``."""
    # Pipecat's development runner prints Unicode box characters. Windows
    # PowerShell may otherwise use cp1252 and fail before the server starts.
    import sys

    import __main__

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    __main__.bot = bot
    main()


if __name__ == "__main__":
    run()
