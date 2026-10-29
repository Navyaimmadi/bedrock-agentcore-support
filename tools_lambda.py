"""Two read-only enterprise-style tools scoped to one synthetic customer."""
import json
import re


def handler(event, context):
    custom = getattr(getattr(context, "client_context", None), "custom", {}) or {}
    tool = custom.get("bedrockAgentCoreToolName", "").split("___")[-1]
    invocation_id = event.get("invocation_id", "")
    if not re.fullmatch(r"[a-f0-9-]{36}", invocation_id):
        raise ValueError("Invalid correlation ID")
    records = {
        "lookup_customer": ("C-100", {"customer_id": "C-100", "name": "Example Company", "plan": "Standard", "status": "active"}),
        "lookup_ticket": ("T-100", {"ticket_id": "T-100", "customer_id": "C-100", "status": "in progress", "issue": "VPN connection"}),
    }
    if tool not in records or event.get("record_id") != records[tool][0]:
        print(json.dumps({"invocation_id": invocation_id, "event": "tool_denied", "tool": tool}))
        raise PermissionError("Record outside the demo principal scope")
    print(json.dumps({"invocation_id": invocation_id, "event": "tool_executed", "tool": tool}))
    return records[tool][1]
