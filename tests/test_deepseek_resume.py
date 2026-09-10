import asyncio
import json
import sys
import types
import unittest
from unittest.mock import patch

# 只为本地 mock 测试提供 Redis 导入桩，不改变生产代码依赖。
redis_asyncio = types.ModuleType("redis.asyncio")
redis_asyncio.Redis = lambda **_kwargs: None
redis_package = types.ModuleType("redis")
redis_package.asyncio = redis_asyncio
sys.modules.setdefault("redis", redis_package)
sys.modules.setdefault("redis.asyncio", redis_asyncio)

httpx_stub = types.ModuleType("httpx")
httpx_stub.Response = object
sys.modules.setdefault("httpx", httpx_stub)

dotenv_stub = types.ModuleType("dotenv")
dotenv_stub.load_dotenv = lambda: None
sys.modules.setdefault("dotenv", dotenv_stub)

pydantic_stub = types.ModuleType("pydantic")
pydantic_stub.BaseModel = object
pydantic_stub.Field = lambda default=None, **_kwargs: default
pydantic_v1_stub = types.ModuleType("pydantic.v1")
pydantic_v1_stub.ConfigDict = dict
sys.modules.setdefault("pydantic", pydantic_stub)
sys.modules.setdefault("pydantic.v1", pydantic_v1_stub)

from cache import deepseek_stream
from crud.deepseek_stream import _iter_sse_data, _trim_history


class FakeRedis:
    def __init__(self):
        self.values = {}
        self.lists = {}
        self.counters = {}
        self.sorted_sets = {}

    async def set(self, key, value, **kwargs):
        if kwargs.get("nx") and key in self.values:
            return False
        self.values[key] = value
        return True

    async def get(self, key):
        return self.values.get(key)

    async def incr(self, key):
        self.counters[key] = self.counters.get(key, 0) + 1
        return self.counters[key]

    async def rpush(self, key, value):
        self.lists.setdefault(key, []).append(value)

    async def expire(self, key, _seconds):
        return True

    async def lrange(self, key, start, end):
        return self.lists.get(key, [])[start:]

    async def zadd(self, key, values):
        self.sorted_sets.setdefault(key, {}).update(values)

    async def zrevrange(self, key, start, end):
        items = sorted(
            self.sorted_sets.get(key, {}).items(),
            key=lambda item: item[1],
            reverse=True,
        )
        return [item[0] for item in items[start:]]


class FakeResponse:
    def __init__(self, lines):
        self.lines = lines

    async def aiter_lines(self):
        for line in self.lines:
            yield line


class DeepSeekResumeTests(unittest.TestCase):
    def test_session_owner_is_claimed_once_and_rejects_other_users(self):
        async def run():
            redis = FakeRedis()
            with patch.object(deepseek_stream, "redis_client", redis):
                self.assertTrue(await deepseek_stream.ensure_session_owner("s1", 7))
                self.assertTrue(await deepseek_stream.ensure_session_owner("s1", 7))
                self.assertFalse(await deepseek_stream.ensure_session_owner("s1", 8))
                sessions = await deepseek_stream.list_sessions(7)
                self.assertEqual(sessions[0]["id"], "s1")

        asyncio.run(run())

    def test_events_are_sequenced_and_replayed_after_last_id(self):
        async def run():
            redis = FakeRedis()
            with patch.object(deepseek_stream, "redis_client", redis):
                self.assertTrue(await deepseek_stream.create_request("r1", "s1", 7))
                self.assertFalse(await deepseek_stream.create_request("r1", "s1", 7))
                await deepseek_stream.append_event("r1", '{"content":"你"}')
                await deepseek_stream.append_event("r1", '{"content":"好"}')
                events = await deepseek_stream.get_events_after("r1", 1)
                self.assertEqual([event["id"] for event in events], [2])

        asyncio.run(run())

    def test_upstream_sse_is_split_into_complete_data_events(self):
        async def run():
            events = [event async for event in _iter_sse_data(FakeResponse([
                'data: {"choices":[{"delta":{"content":"你"}}]}',
                '',
                'data: [DONE]',
                '',
            ]))]
            self.assertEqual(json.loads(events[0])["choices"][0]["delta"]["content"], "你")
            self.assertEqual(events[1], "[DONE]")

        asyncio.run(run())

    def test_history_context_is_bounded_and_keeps_message_pairs_aligned(self):
        history = [
            {"role": "user" if index % 2 == 0 else "assistant", "content": str(index)}
            for index in range(24)
        ]
        trimmed = _trim_history(history)
        self.assertLessEqual(len(trimmed), 20)
        self.assertEqual(trimmed[0]["role"], "user")


if __name__ == "__main__":
    unittest.main()
