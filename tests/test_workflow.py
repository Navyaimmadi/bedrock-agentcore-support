import json
import unittest
from types import SimpleNamespace
from workflow import run_workflow
from tools_lambda import handler


class Gateway:
    def list_tools(self):
        return [{"name": "support___lookup_customer"}, {"name": "support___lookup_ticket"}]
    def call_tool(self, name, args):
        context = SimpleNamespace(client_context=SimpleNamespace(custom={"bedrockAgentCoreToolName": name}))
        return {"content": [{"type": "text", "text": json.dumps(handler(args, context))}]}


class Tests(unittest.TestCase):
    @staticmethod
    def count_tokens(**kwargs):
        return {"inputTokens": 10}

    def test_two_routes(self):
        for route, record in [("customer", "C-100"), ("ticket", "T-100")]:
            calls, logs = [], []
            def converse(**kwargs):
                calls.append(kwargs)
                content = [{"text": route}] if len(calls) == 1 else [{"toolUse": {"toolUseId": "test", "name": "lookup_"+route, "input": {"record_id": record}}}]
                return {"usage": {"inputTokens": 10, "outputTokens": 5}, "output": {"message": {"role": "assistant", "content": content}}}
            result = run_workflow("Check "+record, converse, Gateway(), "offline-fixture", logs.append, self.count_tokens)
            self.assertIn(record, result["answer"])
            self.assertEqual(len(calls), 2)
            self.assertEqual(json.loads(logs[-1])["status"], "success")
            self.assertEqual(len({json.loads(l)["invocation_id"] for l in logs}), 1)

    def test_scope_denial(self):
        context = SimpleNamespace(client_context=SimpleNamespace(custom={"bedrockAgentCoreToolName": "support___lookup_customer"}))
        with self.assertRaises(PermissionError):
            handler({"record_id": "C-999", "invocation_id": "a"*36}, context)

    def test_no_tool_rejected(self):
        responses = iter(["customer", "invented answer"])
        def converse(**kwargs):
            return {"usage": {"inputTokens": 10, "outputTokens": 5}, "output": {"message": {"role": "assistant", "content": [{"text": next(responses)}]}}}
        with self.assertRaises(RuntimeError): run_workflow("customer", converse, Gateway(), "offline", lambda _: None, self.count_tokens)

    def test_invalid_input(self):
        with self.assertRaises(ValueError):run_workflow("", None, None, "offline")

    def test_usage_budget_stops_before_second_request(self):
        calls = []
        def converse(**kwargs):
            calls.append(kwargs)
            return {"usage": {"inputTokens": 4096, "outputTokens": 1}, "output": {"message": {"content": [{"text": "customer"}]}}}
        with self.assertRaises(RuntimeError):
            run_workflow("customer", converse, Gateway(), "offline", lambda _: None, self.count_tokens)
        self.assertEqual(len(calls), 1)

    def test_preflight_rejects_before_inference(self):
        calls = []
        with self.assertRaises(RuntimeError):
            run_workflow("customer", lambda **kw: calls.append(kw), Gateway(), "offline", lambda _: None,
                         lambda **kw: {"inputTokens": 4097})
        self.assertEqual(calls, [])


if __name__ == "__main__": unittest.main()
