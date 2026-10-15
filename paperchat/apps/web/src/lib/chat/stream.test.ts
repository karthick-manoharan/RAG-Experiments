import { afterEach, describe, expect, it, vi } from "vitest";
import {
  ChatEvent,
  createSSEParser,
  questionError,
  streamChat,
} from "./stream";
const frame = (type: string, data: unknown) =>
  `event: ${type}\ndata: ${JSON.stringify(data)}\n\n`;
const encoder = new TextEncoder();
export function controlled() {
  let controller!: ReadableStreamDefaultController<Uint8Array>;
  const cancel = vi.fn();
  const body = new ReadableStream<Uint8Array>({
    start(c) {
      controller = c;
    },
    cancel,
  });
  return {
    response: new Response(body, {
      headers: { "Content-Type": "text/event-stream" },
    }),
    push: (s: string) => controller.enqueue(encoder.encode(s)),
    close: () => controller.close(),
    cancel,
  };
}
afterEach(() => vi.unstubAllGlobals());
describe("SSE", () => {
  it("handles every byte boundary, Unicode, CRLF, comments, multiline data and unknown events", () => {
    const events: ChatEvent[] = [];
    const parser = createSSEParser((e) => events.push(e));
    const text =
      ': hello\r\nevent: future\r\ndata: invalid\r\n\r\nevent: token\r\ndata: {\r\ndata: "text": "α😀"}\r\n\r\n' +
      frame("done", {});
    const decoder = new TextDecoder();
    for (const byte of encoder.encode(text))
      parser.push(decoder.decode(new Uint8Array([byte]), { stream: true }));
    parser.push(decoder.decode());
    parser.finish();
    expect(events).toEqual([{ type: "token", text: "α😀" }, { type: "done" }]);
  });
  it("handles coalesced frames and preserves nullable sources", () => {
    const events: ChatEvent[] = [];
    const parser = createSSEParser((e) => events.push(e));
    const s = {
      id: "S1",
      document_id: null,
      source: null,
      page: null,
      chunk_index: null,
      snippet: "text",
    };
    parser.push(
      frame("sources", { sources: [s] }) +
        frame("token", { text: "one" }) +
        frame("token", { text: " two" }),
    );
    parser.finish();
    expect(events).toEqual([
      { type: "sources", sources: [s] },
      { type: "token", text: "one" },
      { type: "token", text: " two" },
    ]);
  });
  it.each([
    "event: token\ndata: nope\n\n",
    frame("token", { delta: "wrong" }),
    frame("sources", { sources: [{}] }),
    frame("error", {}),
  ])("rejects malformed known events: %s", (text) => {
    expect(() => createSSEParser(() => {}).push(text)).toThrow("invalid");
  });
  it("rejects incomplete frames", () => {
    const p = createSSEParser(() => {});
    p.push("event: token\ndata: {}");
    expect(() => p.finish()).toThrow();
  });
  it("checks length before trimming using Unicode characters", () => {
    expect(questionError(" ".repeat(4001))).toContain("4000");
    expect(questionError("😀".repeat(4000))).toBeUndefined();
    expect(questionError("  ")).toContain("Enter");
  });
});
describe("fetch client", () => {
  it("delivers tokens before completion and sends only the current question", async () => {
    const c = controlled(),
      emit = vi.fn(),
      fetcher = vi.fn().mockResolvedValue(c.response);
    vi.stubGlobal("fetch", fetcher);
    const promise = streamChat(" q ", new AbortController().signal, emit);
    c.push(frame("token", { text: "partial" }));
    await vi.waitFor(() =>
      expect(emit).toHaveBeenCalledWith({ type: "token", text: "partial" }),
    );
    expect(fetcher.mock.calls[0][0]).toBe(
      "http://localhost:8000/api/v1/chat/stream",
    );
    expect(JSON.parse(fetcher.mock.calls[0][1].body)).toEqual({
      question: "q",
    });
    c.push(frame("done", {}));
    await promise;
    expect(c.cancel).toHaveBeenCalled();
  });
  it("normalizes configured base URL", async () => {
    vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "http://localhost:9000/");
    const fetcher = vi
      .fn()
      .mockResolvedValue(
        new Response(frame("done", {}), {
          headers: { "content-type": "text/event-stream" },
        }),
      );
    vi.stubGlobal("fetch", fetcher);
    await streamChat("q", new AbortController().signal, () => {});
    expect(fetcher.mock.calls[0][0]).toBe(
      "http://localhost:9000/api/v1/chat/stream",
    );
    vi.unstubAllEnvs();
  });
  it.each([422, 502, 503, 504])(
    "shows documented HTTP %s errors",
    async (status) => {
      vi.stubGlobal(
        "fetch",
        vi
          .fn()
          .mockResolvedValue(
            new Response(
              JSON.stringify({
                detail: { code: "failure", message: "Try later" },
              }),
              { status },
            ),
          ),
      );
      await expect(
        streamChat("q", new AbortController().signal, () => {}),
      ).rejects.toThrow("Try later");
    },
  );
  it.each([
    new Response("oops", { status: 500 }),
    new Response(null),
    new Response("html"),
    new Response(frame("token", { text: "partial" }), {
      headers: { "content-type": "text/event-stream" },
    }),
  ])("rejects unexpected response or early EOF", async (response) => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response));
    await expect(
      streamChat("q", new AbortController().signal, () => {}),
    ).rejects.toThrow();
  });
  it("delivers terminal SSE errors", async () => {
    const c = controlled(),
      emit = vi.fn();
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(c.response));
    const p = streamChat("q", new AbortController().signal, emit);
    c.push(frame("error", { code: "generation_failed", message: "Try again" }));
    await p;
    expect(emit).toHaveBeenCalledWith({
      type: "error",
      code: "generation_failed",
      message: "Try again",
    });
  });
  it("aborts pending stream reads and closes the reader", async () => {
    const c = controlled(),
      abort = new AbortController();
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(c.response));
    const p = streamChat("q", abort.signal, () => {});
    await Promise.resolve();
    abort.abort();
    await expect(p).rejects.toMatchObject({ name: "AbortError" });
    expect(c.cancel).toHaveBeenCalled();
  });
  it("passes signal while waiting for headers", async () => {
    const abort = new AbortController();
    const fetcher = vi.fn(
      (_url, options) =>
        new Promise((_resolve, reject) =>
          options.signal.addEventListener("abort", () =>
            reject(options.signal.reason),
          ),
        ),
    );
    vi.stubGlobal("fetch", fetcher);
    const p = streamChat("q", abort.signal, () => {});
    abort.abort();
    await expect(p).rejects.toMatchObject({ name: "AbortError" });
    expect(fetcher.mock.calls[0][1].signal).toBe(abort.signal);
  });
});
