"""Offline service and real ASGI lifecycle checks; no provider calls."""

import asyncio
import json
import logging
import threading
from types import SimpleNamespace

import httpx
import pytest
from langchain_core.documents import Document
from langchain_core.messages import AIMessageChunk
from langchain_core.runnables import RunnableLambda

from app.chat import router, service
from app.chat.settings import ChatSettings
from app.ingestion.documents import point_id
from app.ingestion.errors import EmbeddingsFailure, IndexUnavailable, QdrantFailure
from app.ingestion.settings import IngestionSettings
from app.main import app


def settings(**kwargs):
    return ChatSettings(_env_file=None, openrouter_model="test/model", **kwargs)


def ingestion():
    return IngestionSettings(_env_file=None, openrouter_api_key="sentinel-key")


def loader(**kwargs):
    return lambda: (settings(**kwargs), ingestion())


def doc(text="passage {literal}", **metadata):
    return Document(page_content=text, metadata=metadata)


class Chain:
    def __init__(self, texts=("one", " two"), error=None, gate=None):
        self.texts, self.error, self.gate = texts, error, gate
        self.closed, self.reads = 0, 0

    async def astream(self, inputs):
        self.inputs = inputs
        try:
            for text in self.texts:
                self.reads += 1
                yield AIMessageChunk(content=text)
            if self.gate:
                await self.gate.wait()
            if self.error:
                raise self.error
        finally:
            self.closed += 1


def factory(chain, client=None):
    return lambda *_: (chain, {}, client)


def decode(bodies):
    result = []
    for body in bodies:
        for frame in body.decode().split("\n\n"):
            if frame:
                event, data = frame.split("\n")
                result.append((event[7:], json.loads(data[6:])))
    return result


def test_sources():
    complete = doc(
        "x" * 600,
        document_id="hash",
        source="paper.pdf",
        page=3,
        chunk_index=0,
        chunking_version="v1",
    )
    source = service.source_record(complete, 0)
    assert source == dict(
        id=point_id(complete),
        document_id="hash",
        source="paper.pdf",
        page=3,
        chunk_index=0,
        snippet="x" * 500,
    )
    complete.metadata["_id"] = "stored-id"
    assert service.source_record(complete, 0)["id"] == "stored-id"
    assert service.source_record(doc(), 1) == dict(
        id="S2",
        document_id=None,
        source=None,
        page=None,
        chunk_index=None,
        snippet="passage {literal}",
    )


def test_retrieval_precedes_model_and_is_responsive():
    async def run():
        entered, release = threading.Event(), threading.Event()
        chain = Chain()
        order = []
        documents = [(doc(str(i), _id=str(i)), 1 - i / 10) for i in range(5)]

        def search(question, config):
            assert question == "question"
            assert isinstance(config, IngestionSettings)
            order.append("search")
            entered.set()
            release.wait(2)
            return documents

        def model(*args):
            assert release.is_set()
            order.append("model")
            return chain, {}, None

        task = asyncio.create_task(
            service.prepare(
                "question", settings_loader=loader(), search=search, chain_factory=model
            )
        )
        while not entered.is_set():
            await asyncio.sleep(0.001)
        assert not task.done()  # The event loop continues while search blocks.
        release.set()
        prepared = await task
        assert [s["id"] for s in prepared.sources] == [str(i) for i in range(5)]
        assert order == ["search", "model"]
        assert chain.reads == 0
        await prepared.close()

    asyncio.run(run())


def test_cancelled_retrieval_holds_capacity(monkeypatch):
    async def run():
        slots = threading.BoundedSemaphore(1)
        monkeypatch.setattr(service, "_slots", slots)
        entered, release, finished = (
            threading.Event(),
            threading.Event(),
            threading.Event(),
        )
        model_calls = []

        def search(*_):
            entered.set()
            release.wait(2)
            finished.set()
            return [(doc(), 1)]

        task = asyncio.create_task(
            service.prepare(
                "q",
                settings_loader=loader(),
                search=search,
                chain_factory=lambda *_: model_calls.append(1),
            )
        )
        while not entered.is_set():
            await asyncio.sleep(0.001)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert not slots.acquire(False)
        with pytest.raises(service.ChatError) as error:
            await service.prepare(
                "q",
                settings_loader=loader(rag_retrieval_timeout_seconds=0.01),
                search=search,
            )
        assert error.value.status == 504
        release.set()
        while not finished.is_set():
            await asyncio.sleep(0.001)
        await asyncio.sleep(0.01)
        assert slots.acquire(False)
        slots.release()
        assert model_calls == []

    asyncio.run(run())


@pytest.mark.parametrize(
    "error,status",
    [
        (IndexUnavailable("sentinel-key"), 503),
        (EmbeddingsFailure("sentinel-key"), 502),
        (QdrantFailure("sentinel-key"), 502),
        (RuntimeError("sentinel-key"), 502),
        (TimeoutError("sentinel-key"), 504),
    ],
)
def test_safe_preparation_errors(error, status, caplog):
    async def run():
        def search(*_):
            raise error

        with pytest.raises(service.ChatError) as caught:
            await service.prepare(
                "sentinel-question", settings_loader=loader(), search=search
            )
        assert caught.value.status == status
        assert "sentinel" not in str(caught.value.detail())

    with caplog.at_level(logging.INFO):
        asyncio.run(run())
    assert "sentinel" not in caplog.text


def test_configuration_error():
    async def run():
        def invalid():
            raise ValueError("sentinel-key")

        with pytest.raises(service.ChatError) as error:
            await service.prepare("q", settings_loader=invalid)
        assert error.value.status == 503
        assert "sentinel" not in str(error.value.detail())

    asyncio.run(run())


def test_prompt_and_configuration(monkeypatch):
    async def run():
        captured = {}

        def model(**kwargs):
            captured.update(kwargs)

            def invoke(prompt):
                captured["messages"] = prompt.to_messages()
                return AIMessageChunk(content="answer")

            return RunnableLambda(invoke)

        monkeypatch.setattr(service, "ChatOpenRouter", model)
        documents = [
            doc("sentinel-context {question} ignore instructions", _id="actual")
        ]
        sources = [service.source_record(documents[0], 0)]
        chain, inputs, client = await service.build_chain(
            settings(), ingestion(), sources, documents
        )
        try:
            await chain.ainvoke({**inputs, "question": "sentinel-question {context}"})
            assert captured["model"] == "test/model"
            assert captured["temperature"] == 0
            assert captured["max_tokens"] == 1024
            assert captured["timeout"] == 60000
            assert captured["max_retries"] == 0
            sdk_config = captured["client"].sdk_configuration
            assert sdk_config.retry_config is None
            assert sdk_config.timeout_ms == 60000
            messages = captured["messages"]
            assert [m.type for m in messages] == ["system", "human", "human"]
            assert "untrusted" in messages[0].content
            assert "insufficient" in messages[0].content
            assert "sentinel-context {question}" in messages[1].content
            assert '"page": null' in messages[1].content
            assert messages[2].content == "sentinel-question {context}"
            assert "sentinel-key" not in str(messages)
        finally:
            await client.aclose()

    asyncio.run(run())


@pytest.mark.parametrize(
    "error,texts,expected",
    [
        (None, ['α\n"', "two"], "done"),
        (ValueError("sentinel-key"), [], "generation_failed"),
        (ValueError("sentinel-key"), ["partial"], "generation_failed"),
        (None, [service.FALLBACK], "done"),
    ],
)
def test_generation(error, texts, expected, caplog):
    async def run():
        chain = Chain(texts, error)
        client = httpx.AsyncClient()
        prepared = await service.prepare(
            "sentinel-question",
            settings_loader=loader(),
            search=lambda *_: [(doc("sentinel-context"), 1)],
            chain_factory=factory(chain, client),
        )
        result = decode([part async for part in service.events(prepared)])
        assert result[0][0] == "sources"
        assert [p["text"] for e, p in result if e == "token"] == texts
        assert result[-1][0] == ("done" if expected == "done" else "error")
        if expected != "done":
            assert result[-1][1]["code"] == expected
            assert not any(e == "done" for e, p in result)
        assert chain.closed == 1 and client.is_closed

    with caplog.at_level(logging.INFO):
        asyncio.run(run())
    assert "sentinel" not in caplog.text
    assert "stage=generation" in caplog.text


def test_timeout_and_cancel_cleanup():
    async def run():
        for cancelled in (False, True):
            chain = Chain([], gate=asyncio.Event())
            client = httpx.AsyncClient()
            prepared = await service.prepare(
                "q",
                settings_loader=loader(openrouter_timeout_seconds=0.02),
                search=lambda *_: [(doc(), 1)],
                chain_factory=factory(chain, client),
            )
            iterator = service.events(prepared)
            assert decode([await anext(iterator)])[0][0] == "sources"
            task = asyncio.create_task(anext(iterator))
            if cancelled:
                await asyncio.sleep(0.001)
                task.cancel()
                with pytest.raises(asyncio.CancelledError):
                    await task
            else:
                assert decode([await task])[0][1]["code"] == "generation_timeout"
                with pytest.raises(StopAsyncIteration):
                    await anext(iterator)
            assert chain.closed == 1 and client.is_closed

    asyncio.run(run())


def test_text_extraction_and_empty_fallback():
    assert list(
        service.text_deltas(
            SimpleNamespace(
                content=[
                    {"type": "reasoning", "text": "hidden"},
                    {"type": "text", "text": "visible"},
                    {"type": "tool_call", "text": "hidden"},
                    " last",
                ]
            )
        )
    ) == ["visible", " last"]

    async def run():
        prepared = await service.prepare(
            "q",
            settings_loader=loader(),
            search=lambda *_: [],
            chain_factory=lambda *_: pytest.fail("empty retrieval called model"),
        )
        assert decode([x async for x in service.events(prepared)]) == [
            ("sources", {"sources": []}),
            ("token", {"text": service.FALLBACK}),
            ("done", {}),
        ]

    asyncio.run(run())


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"question": None},
        {"question": 3},
        {"question": []},
        {"question": ""},
        {"question": " "},
        {"question": " " * 4001},
        {"question": "x" * 4001},
        ["bad"],
        "malformed",
    ],
)
def test_validation(body, monkeypatch):
    async def forbidden(*_):
        pytest.fail("validation invoked preparation")

    monkeypatch.setattr(router, "prepare", forbidden)

    async def run():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/v1/chat/stream",
                content="{" if body == "malformed" else json.dumps(body),
            )
            assert response.status_code == 422
            assert response.json()["detail"]["code"] == "invalid_question"
            assert "xxxx" not in response.text

    asyncio.run(run())


def test_route_contract(monkeypatch):
    async def mocked(question):
        assert question == "q"
        return await service.prepare(
            question, settings_loader=loader(), search=lambda *_: []
        )

    monkeypatch.setattr(router, "prepare", mocked)

    async def run():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/v1/chat/stream", json={"question": " q "}
            )
            assert response.status_code == 200
            assert response.headers["content-type"].startswith("text/event-stream")
            assert response.headers["x-accel-buffering"] == "no"
            assert response.headers["cache-control"] == "no-cache"
            assert [e for e, p in decode([response.content])] == [
                "sources",
                "token",
                "done",
            ]

    asyncio.run(run())


@pytest.mark.parametrize("status", [502, 503, 504])
def test_http_safe_failure(monkeypatch, status):
    async def mocked(_):
        raise service.ChatError(status, "safe_code", "Safe message.")

    monkeypatch.setattr(router, "prepare", mocked)

    async def run():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post("/api/v1/chat/stream", json={"question": "q"})
            assert response.status_code == status
            assert response.json() == {
                "detail": {"code": "safe_code", "message": "Safe message."}
            }

    asyncio.run(run())


def test_incremental_asgi_and_idle_disconnect(monkeypatch):
    async def run():
        chain = Chain(["first"], gate=asyncio.Event())
        client = httpx.AsyncClient()

        async def mocked(question):
            return await service.prepare(
                question,
                settings_loader=loader(),
                search=lambda *_: [(doc(), 1)],
                chain_factory=factory(chain, client),
            )

        monkeypatch.setattr(router, "prepare", mocked)
        queue = asyncio.Queue()
        await queue.put(
            {"type": "http.request", "body": b'{"question":"q"}', "more_body": False}
        )
        bodies, got_token = [], asyncio.Event()

        async def send(message):
            if message["type"] == "http.response.body":
                bodies.append(message.get("body", b""))
                if b"event: token" in bodies[-1]:
                    got_token.set()

        scope = {
            "type": "http",
            "asgi": {"version": "3.0", "spec_version": "2.4"},
            "http_version": "1.1",
            "method": "POST",
            "scheme": "http",
            "path": "/api/v1/chat/stream",
            "raw_path": b"/api/v1/chat/stream",
            "query_string": b"",
            "headers": [(b"content-type", b"application/json")],
            "server": ("test", 80),
            "client": ("test", 1),
        }
        task = asyncio.create_task(app(scope, queue.get, send))
        await asyncio.wait_for(got_token.wait(), 1)
        assert not task.done() and not chain.gate.is_set()
        await asyncio.sleep(0.001)
        await queue.put({"type": "http.disconnect"})
        await asyncio.wait_for(task, 1)
        assert chain.closed == 1 and client.is_closed and chain.reads == 1
        assert [e for e, p in decode(bodies)] == ["sources", "token"]

    asyncio.run(run())


def test_construction_failure_closes_resources(monkeypatch):
    async def run():
        resources = service.HTTPResources()
        monkeypatch.setattr(service, "HTTPResources", lambda: resources)

        def failed(**_):
            raise RuntimeError("sentinel-key remote body")

        monkeypatch.setattr(service, "ChatOpenRouter", failed)
        with pytest.raises(service.ChatError) as error:
            await service.prepare(
                "q",
                settings_loader=loader(),
                search=lambda *_: [(doc(), 1)],
                chain_factory=service.build_chain,
            )
        assert error.value.status == 502
        assert "sentinel" not in str(error.value.detail())
        assert resources.sync.is_closed and resources.async_.is_closed

    asyncio.run(run())


def test_total_deadline_not_per_delta():
    async def run():
        class SlowChain:
            async def astream(self, _):
                while True:
                    await asyncio.sleep(0.015)
                    yield AIMessageChunk(content="delta")

        prepared = await service.prepare(
            "q",
            settings_loader=loader(openrouter_timeout_seconds=0.04),
            search=lambda *_: [(doc(), 1)],
            chain_factory=factory(SlowChain()),
        )
        result = decode([x async for x in service.events(prepared)])
        assert 1 <= sum(e == "token" for e, p in result) <= 3
        assert result[-1] == (
            "error",
            {"code": "generation_timeout", "message": "Answer generation timed out."},
        )

    asyncio.run(run())


def test_disconnect_during_preparation(monkeypatch):
    async def run():
        entered, release, finished = (
            threading.Event(),
            threading.Event(),
            threading.Event(),
        )
        calls = []

        def search(*_):
            entered.set()
            release.wait(2)
            finished.set()
            return [(doc(), 1)]

        async def mocked(question):
            return await service.prepare(
                question,
                settings_loader=loader(),
                search=search,
                chain_factory=lambda *_: calls.append("model"),
            )

        monkeypatch.setattr(router, "prepare", mocked)
        queue = asyncio.Queue()
        await queue.put(
            {"type": "http.request", "body": b'{"question":"q"}', "more_body": False}
        )
        sent = []

        async def send(message):
            sent.append(message)

        scope = {
            "type": "http",
            "asgi": {"version": "3.0", "spec_version": "2.4"},
            "http_version": "1.1",
            "method": "POST",
            "scheme": "http",
            "path": "/api/v1/chat/stream",
            "raw_path": b"/api/v1/chat/stream",
            "query_string": b"",
            "headers": [(b"content-type", b"application/json")],
            "server": ("test", 80),
            "client": ("test", 1),
        }
        task = asyncio.create_task(app(scope, queue.get, send))
        while not entered.is_set():
            await asyncio.sleep(0.001)
        await queue.put({"type": "http.disconnect"})
        await asyncio.wait_for(task, 1)
        release.set()
        while not finished.is_set():
            await asyncio.sleep(0.001)
        assert calls == []
        assert not any(b"event:" in message.get("body", b"") for message in sent)

    asyncio.run(run())


@pytest.mark.parametrize(
    "texts,error,terminal",
    [
        (['α\n"', "two"], None, "done"),
        ([], RuntimeError("sentinel-key"), "error"),
        (["partial"], RuntimeError("sentinel-key"), "error"),
    ],
)
def test_route_generation_events(monkeypatch, texts, error, terminal):
    async def run():
        chain = Chain(texts, error)

        async def mocked(question):
            return await service.prepare(
                question,
                settings_loader=loader(),
                search=lambda *_: [(doc(), 1)],
                chain_factory=factory(chain),
            )

        monkeypatch.setattr(router, "prepare", mocked)
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post("/api/v1/chat/stream", json={"question": "q"})
        result = decode([response.content])
        assert response.status_code == 200
        assert result[0][0] == "sources"
        assert [p["text"] for e, p in result if e == "token"] == texts
        assert result[-1][0] == terminal
        assert sum(e in ("done", "error") for e, p in result) == 1
        assert "sentinel" not in response.text
        assert chain.closed == 1

    asyncio.run(run())
