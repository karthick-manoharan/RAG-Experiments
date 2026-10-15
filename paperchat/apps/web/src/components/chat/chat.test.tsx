import {
  act,
  cleanup,
  fireEvent,
  render,
  renderHook,
  screen,
} from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { Chat } from "./chat";
import { useChat } from "./use-chat";
const enc = new TextEncoder();
function response() {
  let c!: ReadableStreamDefaultController<Uint8Array>;
  return {
    response: new Response(
      new ReadableStream({
        start(controller) {
          c = controller;
        },
      }),
      { headers: { "content-type": "text/event-stream" } },
    ),
    push: (type: string, data: unknown) =>
      c.enqueue(
        enc.encode(`event: ${type}\ndata: ${JSON.stringify(data)}\n\n`),
      ),
  };
}
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});
it("accumulates tokens, blocks rapid duplicate submits, and retains independent exchanges", async () => {
  const a = response(),
    b = response();
  const fetcher = vi
    .fn()
    .mockResolvedValueOnce(a.response)
    .mockResolvedValueOnce(b.response);
  vi.stubGlobal("fetch", fetcher);
  const { result } = renderHook(useChat);
  act(() => {
    expect(result.current.submit("first")).toBe(true);
    expect(result.current.submit("duplicate")).toBe(false);
  });
  expect(result.current.exchanges[0].status).toBe("loading");
  await act(async () => {
    a.push("token", { text: "one" });
    a.push("token", { text: " two" });
  });
  expect(result.current.exchanges[0]).toMatchObject({
    text: "one two",
    status: "generating",
  });
  await act(async () => a.push("done", {}));
  act(() => {
    result.current.cancel();
    result.current.submit("second");
  });
  expect(result.current.exchanges[0].status).toBe("completed");
  expect(result.current.exchanges).toHaveLength(2);
  expect(JSON.parse(fetcher.mock.calls[1][1].body)).toEqual({
    question: "second",
  });
});
it.each([false, true])(
  "cancels loading/generating (%s), preserves text and allows another request",
  async (tokens) => {
    const a = response(),
      b = response();
    const fetcher = vi
      .fn()
      .mockResolvedValueOnce(a.response)
      .mockResolvedValueOnce(b.response);
    vi.stubGlobal("fetch", fetcher);
    const { result } = renderHook(useChat);
    act(() => {
      result.current.submit("first");
    });
    if (tokens) await act(async () => a.push("token", { text: "partial" }));
    await act(async () => {
      result.current.cancel();
      result.current.submit("next");
    });
    expect(fetcher.mock.calls[0][1].signal.aborted).toBe(true);
    expect(result.current.exchanges[0]).toMatchObject({
      status: "cancelled",
      text: tokens ? "partial" : "",
    });
    expect(result.current.busy).toBe(true);
    expect(result.current.exchanges[1].status).toBe("loading");
  },
);
it("aborts on unmount", async () => {
  const c = response();
  const fetcher = vi.fn().mockResolvedValue(c.response);
  vi.stubGlobal("fetch", fetcher);
  const { result, unmount } = renderHook(useChat);
  act(() => {
    result.current.submit("q");
  });
  unmount();
  expect(fetcher.mock.calls[0][1].signal.aborted).toBe(true);
});
it("handles keyboard, incremental source display, failures and retry", async () => {
  const a = response(),
    b = response();
  const fetcher = vi
    .fn()
    .mockResolvedValueOnce(a.response)
    .mockResolvedValueOnce(b.response);
  vi.stubGlobal("fetch", fetcher);
  render(<Chat />);
  fireEvent.click(screen.getByText("How does multi-head attention work?"));
  const input = screen.getByLabelText("Question about the paper");
  expect(document.activeElement).toBe(input);
  fireEvent.keyDown(input, { key: "Enter", shiftKey: true });
  expect(fetcher).not.toHaveBeenCalled();
  fireEvent.keyDown(input, { key: "Enter", isComposing: true });
  expect(fetcher).not.toHaveBeenCalled();
  fireEvent.keyDown(input, { key: "Enter" });
  await act(async () => {
    a.push("sources", {
      sources: [
        {
          id: "actual",
          document_id: "hash",
          source: "paper.pdf",
          page: 3,
          chunk_index: 0,
          snippet: "<script>actual excerpt</script>",
        },
        {
          id: "S2",
          document_id: null,
          source: null,
          page: null,
          chunk_index: null,
          snippet: "unknown",
        },
      ],
    });
    a.push("token", { text: "Visible partial answer" });
  });
  expect(screen.getByText("Visible partial answer")).toBeTruthy();
  expect(screen.getByText("paper.pdf · p. 3")).toBeTruthy();
  expect(screen.getByText("Unknown source · Page unknown")).toBeTruthy();
  expect(document.querySelector("script")).toBeNull();
  await act(async () =>
    a.push("error", { code: "failed", message: "Please retry" }),
  );
  expect(screen.getByRole("alert").textContent).toBe("Please retry");
  fireEvent.click(screen.getByText("Retry question"));
  expect(JSON.parse(fetcher.mock.calls[1][1].body)).toEqual({
    question: "How does multi-head attention work?",
  });
  await act(async () => b.push("done", {}));
});
it("validates input and stops generation accessibly", async () => {
  const a = response();
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(a.response));
  render(<Chat />);
  const input = screen.getByLabelText("Question about the paper");
  fireEvent.change(input, { target: { value: " ".repeat(4001) } });
  fireEvent.keyDown(input, { key: "Enter" });
  expect(screen.getByRole("alert").textContent).toContain("4000");
  fireEvent.change(input, { target: { value: "q" } });
  fireEvent.keyDown(input, { key: "Enter" });
  fireEvent.click(screen.getByText("Stop generating"));
  expect(screen.getByText("Cancelled · Answer incomplete")).toBeTruthy();
  expect(document.activeElement).toBe(input);
});
it("pauses scroll following and resumes at the bottom", async () => {
  const a = response();
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(a.response));
  render(<Chat />);
  const history = screen.getByRole("region", { name: "Message history" });
  Object.defineProperties(history, {
    scrollHeight: { configurable: true, value: 1000 },
    clientHeight: { configurable: true, value: 200 },
  });
  fireEvent.change(screen.getByLabelText("Question about the paper"), {
    target: { value: "q" },
  });
  fireEvent.click(screen.getByText("Send question"));
  history.scrollTop = 100;
  fireEvent.scroll(history);
  await act(async () => a.push("token", { text: "first" }));
  expect(history.scrollTop).toBe(100);
  history.scrollTop = 800;
  fireEvent.scroll(history);
  await act(async () => a.push("token", { text: " second" }));
  expect(history.scrollTop).toBe(1000);
});
