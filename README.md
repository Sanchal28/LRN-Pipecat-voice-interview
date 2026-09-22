# LRN voice interview agent

A browser-based voice interviewer built with Pipecat and WebRTC. It listens
with Deepgram, reasons with Groq, and replies using Deepgram's Aura voice.

New to Pipecat? Read the [beginner guide](docs/PIPECAT_GUIDE.md) for an
end-to-end explanation of this project.

## Setup

1. Install [uv](https://docs.astral.sh/uv/).
2. Copy `.env.example` to `.env` and add your provider keys.
3. Run `uv sync` (this installs Pipecat's bundled browser client).
4. Start the voice backend: `uv run lrn-interview-agent -t webrtc`.
5. In a second terminal, start the custom LRN UI:

   ```powershell
   cd web
   npm install
   npm run dev
   ```

6. Open `http://localhost:3000` and choose **Begin interview**. Allow microphone access when your browser asks.

The Pipecat page on port `7860` remains useful for development diagnostics.
The LRN UI on port `3000` is the product-facing interface and connects to the
Pipecat offer endpoint at `http://localhost:7860/api/offer`.

To use a non-local backend, copy `web/.env.local.example` to `web/.env.local`
and set `NEXT_PUBLIC_PIPECAT_URL` to that backend's HTTPS origin.

For an internet-facing deployment, configure a TURN server using Pipecat's
`--ice-servers` option; the default local WebRTC setup is intended for
development.

## Environment

`DEEPGRAM_API_KEY` is used for speech recognition and voice generation.
`GROQ_API_KEY` is used for the interview model.
