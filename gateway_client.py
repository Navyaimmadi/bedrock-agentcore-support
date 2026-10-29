"""Minimal SigV4-authenticated MCP client for AgentCore Gateway."""
import json
from urllib.parse import urlparse
import boto3
import requests
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest


class GatewayClient:
    def __init__(self, url, region):
        parsed = urlparse(url)
        if parsed.scheme != "https" or not parsed.hostname or not parsed.hostname.endswith(".amazonaws.com"):
            raise ValueError("Use the HTTPS gatewayUrl returned by AWS")
        self.url, self.region = url, region
        self.session = boto3.Session(region_name=region)
        self.http = requests.Session()
        self.session_id = None
        self.counter = 0
        self.rpc("initialize", {"protocolVersion": "2025-03-26", "capabilities": {}, "clientInfo": {"name": "support-lab", "version": "1.0"}})
        self.rpc("notifications/initialized", {}, notification=True)

    def rpc(self, method, params, notification=False):
        self.counter += 1
        data = {"jsonrpc": "2.0", "method": method, "params": params}
        if not notification: data["id"] = self.counter
        body = json.dumps(data)
        headers = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream", "MCP-Protocol-Version": "2025-03-26"}
        if self.session_id: headers["Mcp-Session-Id"] = self.session_id
        credentials = self.session.get_credentials()
        if not credentials: raise RuntimeError("AWS role/profile credentials unavailable")
        request = AWSRequest(method="POST", url=self.url, data=body, headers=headers)
        SigV4Auth(credentials.get_frozen_credentials(), "bedrock-agentcore", self.region).add_auth(request)
        response = self.http.post(self.url, data=body, headers=dict(request.headers), timeout=(10, 30), allow_redirects=False)
        response.raise_for_status()
        if 300 <= response.status_code < 400: raise RuntimeError("Unexpected Gateway redirect")
        self.session_id = response.headers.get("Mcp-Session-Id", self.session_id)
        if notification: return {}
        if "text/event-stream" in response.headers.get("Content-Type", ""):
            messages = [json.loads(line[5:].strip()) for line in response.text.splitlines() if line.startswith("data:") and line[5:].strip()]
            result = next((m for m in messages if m.get("id") == self.counter), None)
            if result is None: raise RuntimeError("No matching MCP response")
        else: result = response.json()
        if "error" in result: raise RuntimeError("Gateway MCP error")
        return result["result"]

    def list_tools(self):
        tools, params = [], {}
        for _ in range(10):
            page = self.rpc("tools/list", params)
            tools.extend(page.get("tools", []))
            if not page.get("nextCursor"): return tools
            params = {"cursor": page["nextCursor"]}
        raise RuntimeError("Gateway tool pagination exceeded limit")

    def call_tool(self, name, args):
        return self.rpc("tools/call", {"name": name, "arguments": args})
