export type Source = {
  id: string;
  document_id: string | null;
  source: string | null;
  page: number | null;
  chunk_index: number | null;
  snippet: string;
};
export type ChatEvent =
  | { type: "sources"; sources: Source[] }
  | { type: "token"; text: string }
  | { type: "done" }
  | { type: "error"; code: string; message: string };

const record = (v: unknown): v is Record<string, unknown> =>
  typeof v === "object" && v !== null && !Array.isArray(v);
const nullableString = (v: unknown) => v === null || typeof v === "string";
function source(v: unknown): v is Source {
  return (
    record(v) &&
    typeof v.id === "string" &&
    typeof v.snippet === "string" &&
    nullableString(v.document_id) &&
    nullableString(v.source) &&
    (v.page === null || (Number.isInteger(v.page) && Number(v.page) > 0)) &&
    (v.chunk_index === null ||
      (Number.isInteger(v.chunk_index) && Number(v.chunk_index) >= 0))
  );
}
export class StreamError extends Error {}
const invalid = () =>
  new StreamError("The answer stream was invalid. Please try again.");

/** Incremental line parser. CR is held until its optional LF arrives. */
export function createSSEParser(emit: (event: ChatEvent) => void) {
  let buffer = "",
    name = "",
    data: string[] = [];
  function line(value: string) {
    if (!value) {
      if (data.length && ["sources", "token", "done", "error"].includes(name)) {
        let payload: unknown;
        try {
          payload = JSON.parse(data.join("\n"));
        } catch {
          throw invalid();
        }
        if (!record(payload)) throw invalid();
        if (
          name === "sources" &&
          Array.isArray(payload.sources) &&
          payload.sources.every(source)
        )
          emit({ type: "sources", sources: payload.sources });
        else if (name === "token" && typeof payload.text === "string")
          emit({ type: "token", text: payload.text });
        else if (name === "done" && Object.keys(payload).length === 0)
          emit({ type: "done" });
        else if (
          name === "error" &&
          typeof payload.code === "string" &&
          typeof payload.message === "string"
        )
          emit({ type: "error", code: payload.code, message: payload.message });
        else throw invalid();
      }
      name = "";
      data = [];
      return;
    }
    if (value.startsWith(":")) return;
    const colon = value.indexOf(":");
    const field = colon < 0 ? value : value.slice(0, colon);
    let content = colon < 0 ? "" : value.slice(colon + 1);
    if (content.startsWith(" ")) content = content.slice(1);
    if (field === "event") name = content;
    if (field === "data") data.push(content);
  }
  return {
    push(text: string) {
      buffer += text;
      for (;;) {
        const i = buffer.search(/[\r\n]/);
        if (i < 0 || (buffer[i] === "\r" && i === buffer.length - 1)) break;
        const width = buffer[i] === "\r" && buffer[i + 1] === "\n" ? 2 : 1;
        const value = buffer.slice(0, i);
        buffer = buffer.slice(i + width);
        line(value);
      }
    },
    finish() {
      if (buffer || data.length || name) throw invalid();
    },
  };
}

export function questionError(question: string): string | undefined {
  if ([...question].length > 4000) return "Use at most 4000 characters.";
  if (!question.trim()) return "Enter a question about the paper.";
}

export async function streamChat(
  question: string,
  signal: AbortSignal,
  emit: (event: ChatEvent) => void,
) {
  const validation = questionError(question);
  if (validation) throw new StreamError(validation);
  signal.throwIfAborted();
  const base = (
    process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000"
  ).replace(/\/+$/, "");
  const response = await fetch(`${base}/api/v1/chat/stream`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "text/event-stream",
    },
    body: JSON.stringify({ question: question.trim() }),
    signal,
  });
  signal.throwIfAborted();
  if (!response.ok) {
    let message = `Unable to answer right now (${response.status}). Please try again.`;
    try {
      const body: unknown = await response.json();
      if (
        record(body) &&
        record(body.detail) &&
        typeof body.detail.message === "string"
      )
        message = body.detail.message;
    } catch {
      /* Non-JSON failures use the local message. */
    }
    throw new StreamError(message);
  }
  if (
    !response.body ||
    !response.headers.get("content-type")?.startsWith("text/event-stream")
  )
    throw invalid();
  const reader = response.body.getReader();
  const decoder = new TextDecoder("utf-8", { fatal: true });
  let terminal = false;
  const parser = createSSEParser((event) => {
    signal.throwIfAborted();
    if (terminal) return;
    terminal = event.type === "done" || event.type === "error";
    emit(event);
  });
  const abort = () => {
    void reader.cancel().catch(() => {});
  };
  signal.addEventListener("abort", abort, { once: true });
  try {
    while (!terminal) {
      signal.throwIfAborted();
      const { value, done } = await reader.read();
      signal.throwIfAborted();
      if (done) {
        parser.push(decoder.decode());
        parser.finish();
        if (!terminal)
          throw new StreamError(
            "The answer stream ended early. Please try again.",
          );
        break;
      }
      parser.push(decoder.decode(value, { stream: true }));
    }
  } finally {
    signal.removeEventListener("abort", abort);
    await reader.cancel().catch(() => {});
    reader.releaseLock();
  }
}
