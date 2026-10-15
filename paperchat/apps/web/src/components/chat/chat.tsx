"use client";
import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { questionError } from "@/lib/chat/stream";
import { useChat } from "./use-chat";

const examples = [
  "How does multi-head attention work?",
  "Why does the Transformer use positional encoding?",
  "How is the decoder different from the encoder?",
];
export function Chat() {
  const { exchanges, busy, submit, cancel } = useChat();
  const [draft, setDraft] = useState("");
  const [validation, setValidation] = useState<string>();
  const composer = useRef<HTMLTextAreaElement>(null);
  const history = useRef<HTMLDivElement>(null);
  const following = useRef(true);
  useEffect(() => {
    if (following.current && history.current)
      history.current.scrollTop = history.current.scrollHeight;
  }, [exchanges]);
  function send(question = draft) {
    const error = questionError(question);
    setValidation(error);
    if (!error && submit(question)) {
      setDraft("");
      composer.current?.focus();
    }
  }
  const latest = exchanges.at(-1);
  return (
    <main className="mx-auto flex h-dvh max-w-4xl flex-col px-4 sm:px-8">
      <header className="border-b py-5 sm:py-7">
        <p className="mb-2 text-xs font-semibold uppercase tracking-[0.2em] text-muted-foreground">
          PaperChat · Paper companion
        </p>
        <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">
          Attention Is All You Need
        </h1>
        <p className="mt-2 text-sm text-muted-foreground">
          Explore the Transformer, one question at a time. Answers grounded in
          the paper.
        </p>
      </header>
      <div
        ref={history}
        role="region"
        aria-label="Message history"
        tabIndex={0}
        onScroll={() => {
          const el = history.current!;
          following.current =
            el.scrollHeight - el.scrollTop - el.clientHeight < 64;
        }}
        className="min-h-0 flex-1 overflow-y-auto overscroll-contain py-6 focus-visible:outline-2 focus-visible:outline-ring"
      >
        {!exchanges.length && (
          <section className="mx-auto max-w-xl py-6 sm:py-12">
            <p className="text-xl font-medium">
              What would you like to understand?
            </p>
            <p className="mt-2 mb-5 text-sm text-muted-foreground">
              Start with a question, or try one of these.
            </p>
            <div className="flex flex-col gap-3">
              {examples.map((q) => (
                <Button
                  key={q}
                  variant="outline"
                  className="h-auto justify-start whitespace-normal px-4 py-3 text-left"
                  onClick={() => {
                    setDraft(q);
                    composer.current?.focus();
                  }}
                >
                  {q}
                </Button>
              ))}
            </div>
          </section>
        )}
        <ol className="space-y-8">
          {exchanges.map((e) => (
            <li key={e.id} className="space-y-4">
              <article
                aria-label="Your question"
                className="ml-auto max-w-[90%] rounded-2xl bg-muted px-4 py-3 sm:max-w-[80%]"
              >
                <h2 className="mb-1 text-xs font-semibold text-muted-foreground">
                  You
                </h2>
                <p className="whitespace-pre-wrap break-words">{e.question}</p>
              </article>
              <article aria-label="Assistant response" className="min-w-0 px-1">
                <h2 className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  PaperChat
                </h2>
                <p className="whitespace-pre-wrap break-words text-base leading-7">
                  {e.text ||
                    (e.status === "loading"
                      ? "Finding relevant passages…"
                      : "No answer received.")}
                </p>
                <p className="mt-2 text-xs text-muted-foreground">
                  {e.status === "loading"
                    ? "Loading"
                    : e.status === "generating"
                      ? "Generating…"
                      : e.status === "completed"
                        ? "Completed"
                        : `${e.status === "cancelled" ? "Cancelled" : "Failed"} · Answer incomplete`}
                </p>
                {e.error && (
                  <p role="alert" className="mt-3 text-sm text-destructive">
                    {e.error}
                  </p>
                )}
                {e.status === "failed" && (
                  <Button
                    className="mt-3"
                    variant="outline"
                    disabled={busy}
                    onClick={() => send(e.question)}
                  >
                    Retry question
                  </Button>
                )}
                {!!e.sources.length && (
                  <section aria-label="Sources" className="mt-4 border-t pt-3">
                    <h3 className="mb-2 text-xs font-semibold text-muted-foreground">
                      Retrieved sources
                    </h3>
                    <ul className="flex flex-wrap gap-2">
                      {e.sources.map((s, i) => (
                        <li key={`${s.id}-${i}`} className="min-w-0 max-w-full">
                          <details className="rounded-lg border px-3 py-2 text-xs">
                            <summary className="cursor-pointer break-words">
                              {s.source ?? "Unknown source"}
                              {s.page !== null
                                ? ` · p. ${s.page}`
                                : " · Page unknown"}
                            </summary>
                            <p className="mt-2 break-all text-muted-foreground">
                              Source ID: {s.id}
                            </p>
                            <p className="mt-2 max-w-lg whitespace-pre-wrap break-words leading-5">
                              {s.snippet}
                            </p>
                          </details>
                        </li>
                      ))}
                    </ul>
                  </section>
                )}
              </article>
            </li>
          ))}
        </ol>
      </div>
      <footer className="border-t bg-background py-4">
        <p role="status" className="mb-2 text-xs text-muted-foreground">
          {busy
            ? latest?.status === "generating"
              ? "Generating answer…"
              : "Retrieving context…"
            : latest
              ? `Answer ${latest.status}.`
              : "Ask about the paper"}
        </p>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            send();
          }}
        >
          <label htmlFor="question" className="sr-only">
            Question about the paper
          </label>
          <Textarea
            ref={composer}
            id="question"
            value={draft}
            aria-describedby="composer-help composer-error"
            aria-invalid={!!validation}
            placeholder="Ask a question about the paper…"
            className="max-h-40 resize-y"
            onChange={(e) => {
              setDraft(e.target.value);
              setValidation(undefined);
            }}
            onKeyDown={(e) => {
              if (
                e.key === "Enter" &&
                !e.shiftKey &&
                !e.nativeEvent.isComposing &&
                e.keyCode !== 229
              ) {
                e.preventDefault();
                send();
              }
            }}
          />
          <p
            id="composer-error"
            className="mt-1 text-sm text-destructive"
            role={validation ? "alert" : undefined}
          >
            {validation}
          </p>
          <div className="mt-2 flex items-center justify-between gap-3">
            <p id="composer-help" className="text-xs text-muted-foreground">
              Enter to send · Shift+Enter for a new line
            </p>
            {busy ? (
              <Button
                type="button"
                variant="outline"
                onClick={() => {
                  cancel();
                  composer.current?.focus();
                }}
              >
                Stop generating
              </Button>
            ) : (
              <Button type="submit" disabled={!draft.trim()}>
                Send question
              </Button>
            )}
          </div>
        </form>
        <p className="mt-3 text-center text-[11px] text-muted-foreground">
          Each question is independent. Check the retrieved sources for context.
        </p>
      </footer>
    </main>
  );
}
