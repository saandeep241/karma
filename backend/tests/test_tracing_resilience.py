"""Offline regression tests: telemetry must not retry work or replace its errors.

Run from backend with AI and auth disabled:
    python -m unittest discover -s tests -v
"""
from types import SimpleNamespace as NS
import unittest
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException

import app.agents.base_agent as base
import app.langfuse_client as tracing


class Telemetry:
    def __init__(self, failure=None, suppress=False):
        self.failure = failure
        self.suppress = suppress

    def start_as_current_observation(self, **kwargs):
        if self.failure == "start":
            raise RuntimeError("telemetry start")
        return self

    def __enter__(self):
        if self.failure == "enter":
            raise RuntimeError("telemetry enter")
        return self

    def __exit__(self, *args):
        if self.failure == "exit":
            raise RuntimeError("telemetry exit")
        return self.suppress

    def update_current_generation(self, **kwargs):
        if self.failure == "update":
            raise RuntimeError("telemetry update")

    def flush(self):
        if self.failure == "flush":
            raise RuntimeError("telemetry flush")


class Agent(base.BaseAgent):
    AGENT_NAME = "OfflineTest"

    async def run(self):
        pass


def response(content="result", tools=None):
    return NS(choices=[NS(message=NS(role="assistant", content=content, tool_calls=tools))],
              usage=NS(prompt_tokens=10, completion_tokens=5, total_tokens=15))


class TracingResilienceTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.agent = Agent()
        self.agent.dummy_mode = False
        self.create = unittest.mock.Mock(return_value=response())
        self.agent.client = NS(chat=NS(completions=NS(create=self.create)))

    async def test_simple_completion_once_for_each_telemetry_failure(self):
        for failure in ("start", "enter", "update", "exit", "flush"):
            with self.subTest(failure=failure), patch.object(
                    base, "get_langfuse", return_value=Telemetry(failure)):
                self.create.reset_mock()
                self.assertEqual(await self.agent._simple_completion("offline"), "result")
                self.assertEqual(self.create.call_count, 1)

    async def test_tool_side_effect_and_models_not_retried(self):
        tool = NS(id="offline-call", type="function",
                  function=NS(name="offline_tool", arguments='{"value": 1}'))
        for failure in (None, "start", "enter", "update", "exit", "flush"):
            with self.subTest(failure=failure), patch.object(
                    base, "get_langfuse", return_value=Telemetry(failure)), patch.object(
                    base, "execute_tool", return_value={"ok": True}) as execute:
                self.create.reset_mock()
                self.create.side_effect = [response(None, [tool]), response()]
                result = await self.agent._completion_with_tools("offline", tools=["offline_tool"])
                self.assertEqual(result["response"], "result")
                self.assertEqual(result["iterations"], 2)
                self.assertEqual(self.create.call_count, 2)
                execute.assert_called_once_with("offline_tool", {"value": 1})

    async def test_max_iterations_flush_failure_does_not_repeat_tool(self):
        tool = NS(id="offline-call", type="function",
                  function=NS(name="offline_tool", arguments="{}"))
        self.create.return_value = response(None, [tool])
        with patch.object(base, "get_langfuse", return_value=Telemetry("flush")), patch.object(
                base, "execute_tool", return_value={"ok": True}) as execute:
            result = await self.agent._completion_with_tools("offline", max_iterations=1)
        self.assertTrue(result["max_iterations_reached"])
        self.assertEqual(self.create.call_count, 1)
        self.assertEqual(execute.call_count, 1)

    async def test_real_model_errors_preserved_without_retry(self):
        original = RuntimeError("model unavailable")
        for method in ("_simple_completion", "_completion_with_tools"):
            for failure in ("start", "exit", None):
                with self.subTest(method=method, failure=failure), patch.object(
                        base, "get_langfuse", return_value=Telemetry(failure, suppress=True)):
                    self.create.reset_mock()
                    self.create.side_effect = original
                    with self.assertRaises(RuntimeError) as raised:
                        await getattr(self.agent, method)("offline")
                    self.assertIs(raised.exception, original)
                    self.assertEqual(self.create.call_count, 1)

    async def test_tool_errors_preserved_without_retry(self):
        tool = NS(id="offline-call", type="function",
                  function=NS(name="offline_tool", arguments="{}"))
        original = RuntimeError("tool unavailable")
        self.create.return_value = response(None, [tool])
        with patch.object(base, "get_langfuse", return_value=Telemetry("exit")), patch.object(
                base, "execute_tool", side_effect=original) as execute:
            with self.assertRaises(RuntimeError) as raised:
                await self.agent._completion_with_tools("offline")
        self.assertIs(raised.exception, original)
        self.assertEqual(self.create.call_count, 1)
        self.assertEqual(execute.call_count, 1)

    async def test_token_limit_rejection_stays_rejected(self):
        with patch.object(self.agent, "_check_token_limit",
                          new=AsyncMock(return_value=(False, {}))):
            for method in ("_simple_completion", "_completion_with_tools"):
                with self.assertRaises(HTTPException) as raised:
                    await getattr(self.agent, method)("offline", user_id="offline")
                self.assertEqual(raised.exception.status_code, 429)
        self.create.assert_not_called()

    async def test_disabled_tracing_still_calls_model_once(self):
        with patch.object(base, "get_langfuse", return_value=None):
            self.assertEqual(await self.agent._simple_completion("offline"), "result")
        self.assertEqual(self.create.call_count, 1)

    def test_root_start_enter_exit_flush_failures_are_nonblocking(self):
        for failure in ("start", "enter", "exit", "flush"):
            with self.subTest(failure=failure), patch.object(
                    tracing, "get_langfuse", return_value=Telemetry(failure)):
                executions = []
                with tracing.root_trace("offline"):
                    executions.append("executed")
                self.assertEqual(executions, ["executed"])

    def test_root_application_error_preserved_even_if_exit_and_flush_fail(self):
        original = RuntimeError("application failed")
        class BrokenExitAndFlush(Telemetry):
            def flush(self):
                raise RuntimeError("telemetry flush")
        with patch.object(tracing, "get_langfuse", return_value=BrokenExitAndFlush("exit")):
            with self.assertRaises(RuntimeError) as raised:
                with tracing.root_trace("offline"):
                    raise original
        self.assertIs(raised.exception, original)

    def test_context_cannot_suppress_application_error(self):
        original = RuntimeError("application failed")
        with self.assertRaises(RuntimeError) as raised:
            with tracing.safe_observation(Telemetry(suppress=True), name="offline"):
                raise original
        self.assertIs(raised.exception, original)

    def test_failure_logged_as_warning(self):
        with self.assertLogs("karma.langfuse", level="WARNING") as logged:
            tracing.safe_update_generation(Telemetry("update"), output="offline")
        self.assertIn("generation update failed", logged.output[0])


if __name__ == "__main__":
    unittest.main()
