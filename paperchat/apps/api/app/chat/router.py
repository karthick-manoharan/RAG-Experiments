"""HTTP validation and a single-owner ASGI disconnect lifecycle."""

import asyncio
from contextlib import suppress

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field, ValidationError, field_validator
from starlette.responses import Response, StreamingResponse

from app.chat.service import ChatError, events, prepare, sse

router = APIRouter()


class Question(BaseModel):
    question: str = Field(strict=True, max_length=4000)

    @field_validator("question")
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError("must not be blank")
        return value.strip()


async def disconnect(receive):
    while True:
        if (await receive())["type"] == "http.disconnect":
            return


async def cancel(task):
    task.cancel()
    with suppress(asyncio.CancelledError, Exception):
        await task


class ChatResponse(StreamingResponse):
    def __init__(self, prepared, watcher):
        super().__init__(
            events(prepared),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )
        self.prepared, self.watcher = prepared, watcher

    async def __call__(self, scope, receive, send):
        # Do not invoke StreamingResponse.__call__: it may create a competing
        # receive consumer. The watcher transfers from preparation to streaming.
        async def stream():
            await send(
                {
                    "type": "http.response.start",
                    "status": self.status_code,
                    "headers": self.raw_headers,
                }
            )
            try:
                async for body in self.body_iterator:
                    await send(
                        {"type": "http.response.body", "body": body, "more_body": True}
                    )
            except (asyncio.CancelledError, OSError):
                raise
            except Exception:
                await send(
                    {
                        "type": "http.response.body",
                        "more_body": True,
                        "body": sse(
                            "error",
                            {
                                "code": "stream_failed",
                                "message": "The answer stream failed.",
                            },
                        ),
                    }
                )
            await send({"type": "http.response.body", "body": b"", "more_body": False})

        task = asyncio.create_task(stream())
        try:
            await asyncio.wait(
                [task, self.watcher], return_when=asyncio.FIRST_COMPLETED
            )
            if self.watcher.done():
                await cancel(task)
            else:
                await task
        finally:
            await cancel(task)
            await cancel(self.watcher)
            await self.body_iterator.aclose()
            await self.prepared.close()


@router.post("/api/v1/chat/stream")
async def chat_stream(request: Request):
    try:
        question = Question.model_validate(await request.json()).question
    except (ValidationError, ValueError, UnicodeDecodeError):
        raise HTTPException(
            422,
            detail={
                "code": "invalid_question",
                "message": "Provide a nonblank string of at most 4000 characters.",
            },
        ) from None
    watcher = asyncio.create_task(disconnect(request.receive))
    pending = asyncio.create_task(prepare(question))
    transferred = False
    try:
        await asyncio.wait([pending, watcher], return_when=asyncio.FIRST_COMPLETED)
        if watcher.done():
            await cancel(pending)
            if not pending.cancelled() and pending.exception() is None:
                await pending.result().close()
            return Response(status_code=204)
        prepared = await pending
        transferred = True
        return ChatResponse(prepared, watcher)
    except ChatError as error:
        raise HTTPException(error.status, detail=error.detail()) from None
    finally:
        if not transferred:
            await cancel(pending)
            await cancel(watcher)
