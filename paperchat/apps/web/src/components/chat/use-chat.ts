"use client";
import { useEffect, useRef, useState } from "react";
import {
  questionError,
  Source,
  StreamError,
  streamChat,
} from "@/lib/chat/stream";

export type Status =
  | "loading"
  | "generating"
  | "completed"
  | "cancelled"
  | "failed";
export type Exchange = {
  id: string;
  question: string;
  text: string;
  sources: Source[];
  status: Status;
  error?: string;
};
export function useChat() {
  const [exchanges, setExchanges] = useState<Exchange[]>([]);
  const active = useRef<{ id: string; controller: AbortController } | null>(
    null,
  );
  const [busy, setBusy] = useState(false);
  useEffect(
    () => () => {
      active.current?.controller.abort();
      active.current = null;
    },
    [],
  );
  function update(id: string, patch: (e: Exchange) => Exchange) {
    setExchanges((items) => items.map((e) => (e.id === id ? patch(e) : e)));
  }
  function finish(id: string, status: Status, error?: string) {
    if (active.current?.id !== id) return;
    active.current = null;
    setBusy(false);
    update(id, (e) => ({ ...e, status, error }));
  }
  function submit(question: string) {
    if (active.current || questionError(question)) return false;
    const id = crypto.randomUUID(),
      controller = new AbortController();
    active.current = { id, controller };
    setBusy(true);
    setExchanges((items) => [
      ...items,
      { id, question, text: "", sources: [], status: "loading" },
    ]);
    void streamChat(question, controller.signal, (event) => {
      if (active.current?.id !== id || controller.signal.aborted) return;
      if (event.type === "token")
        update(id, (e) => ({
          ...e,
          text: e.text + event.text,
          status: "generating",
        }));
      if (event.type === "sources")
        update(id, (e) => ({ ...e, sources: event.sources }));
      if (event.type === "done") finish(id, "completed");
      if (event.type === "error") finish(id, "failed", event.message);
    }).catch((error) => {
      if (controller.signal.aborted) finish(id, "cancelled");
      else
        finish(
          id,
          "failed",
          error instanceof StreamError
            ? error.message
            : "Could not connect to the answer service. Please try again.",
        );
    });
    return true;
  }
  function cancel() {
    const request = active.current;
    if (request) {
      request.controller.abort();
      finish(request.id, "cancelled");
    }
  }
  return { exchanges, busy, submit, cancel };
}
