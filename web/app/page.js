"use client";

import { useEffect, useState } from "react";
import {
  PipecatClientAudio,
  PipecatClientProvider,
  usePipecatClient,
  usePipecatClientTransportState,
} from "@pipecat-ai/client-react";
import { PipecatClient } from "@pipecat-ai/client-js";
import { SmallWebRTCTransport } from "@pipecat-ai/small-webrtc-transport";

const QUESTIONS = ["Introduction", "Accounting", "Valuation", "Enterprise value", "Markets", "Reflection"];
const PIPECAT_URL = process.env.NEXT_PUBLIC_PIPECAT_URL || "http://localhost:7860";

function InterviewRoom() {
  const client = usePipecatClient();
  const transportState = usePipecatClientTransportState();
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [connectionError, setConnectionError] = useState("");

  const connected = transportState === "ready";
  const connecting = transportState === "connecting";
  const status = connectionError ? "Connection failed" : connected ? "Listening" : connecting ? "Connecting" : "Ready to begin";

  useEffect(() => {
    if (!connected) return;
    const interval = window.setInterval(() => setElapsedSeconds((time) => time + 1), 1000);
    return () => window.clearInterval(interval);
  }, [connected]);

  async function startInterview() {
    setElapsedSeconds(0);
    setConnectionError("");
    if (!client) return;
    try {
      await client.connect({
        webrtcRequestParams: { endpoint: `${PIPECAT_URL}/api/offer` },
      });
    } catch {
      setConnectionError(`Cannot reach the voice server at ${PIPECAT_URL}. Start the Pipecat backend, then try again.`);
    }
  }

  async function endInterview() {
    if (!client) return;
    await client.disconnect();
  }

  const minutes = String(Math.floor(elapsedSeconds / 60)).padStart(2, "0");
  const seconds = String(elapsedSeconds % 60).padStart(2, "0");

  return (
    <main>
      <PipecatClientAudio />
      <nav><span className="wordmark">LRN</span><span className="mode">INVESTMENT BANKING · TECHNICAL</span><span className="timer">{minutes}:{seconds}</span></nav>
      <section className="stage">
        <p className="eyeline">Mock interview</p>
        <h1>Tell the story<br />behind your numbers.</h1>
        <p className="intro">Six focused questions. One uninterrupted conversation. Your practice report follows the session.</p>
        <div className={`voice-orb ${connected ? "active" : ""}`} aria-label={status}><span /><span /><span /></div>
        <p className="status"><i /> {status}</p>
        {connectionError && <p className="connection-error" role="alert">{connectionError}</p>}
        <div className="actions">
          {!connected ? <button disabled={connecting} onClick={startInterview}>{connecting ? "Connecting…" : "Begin interview"} <b>↗</b></button> : <button className="end" onClick={endInterview}>End interview</button>}
        </div>
      </section>
      <aside className="rail" aria-label="Interview progress">
        <p>SESSION PROGRESS</p>
        {QUESTIONS.map((question, index) => <div className={connected && index === 0 ? "current" : ""} key={question}><span>{String(index + 1).padStart(2, "0")}</span>{question}</div>)}
      </aside>
      <footer>MICROPHONE {connected ? "CONNECTED" : "OFFLINE"}<span>·</span> PRIVATE PRACTICE SESSION</footer>
    </main>
  );
}

export default function Page() {
  const [client, setClient] = useState(null);

  useEffect(() => {
    setClient(new PipecatClient({ transport: new SmallWebRTCTransport() }));
  }, []);

  if (!client) return <main aria-busy="true" />;
  return <PipecatClientProvider client={client}><InterviewRoom /></PipecatClientProvider>;
}
