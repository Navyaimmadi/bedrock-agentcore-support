import argparse
import json
import uuid
from pathlib import Path
import boto3
from botocore.config import Config

p = argparse.ArgumentParser()
p.add_argument("--prompt", default="Look up customer C-100")
p.add_argument("--allow-paid", action="store_true")
a = p.parse_args()
if not a.allow_paid: p.error("Invocation incurs AWS usage; pass --allow-paid to proceed")
state = json.loads(Path("deployment.json").read_text())
client = boto3.client("bedrock-agentcore", region_name=state["region"], config=Config(connect_timeout=10, read_timeout=120, retries={"total_max_attempts": 1}))
response = client.invoke_agent_runtime(agentRuntimeArn=state["runtime_arn"], runtimeSessionId=str(uuid.uuid4()),
    payload=json.dumps({"prompt": a.prompt}).encode(), contentType="application/json")
print(response["response"].read().decode())
