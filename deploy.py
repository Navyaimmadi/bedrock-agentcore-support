"""Create lab AWS resources after explicit --execute. Existing resources are not overwritten."""
import argparse
import io
import json
from pathlib import Path
import time
from zipfile import ZipFile
import boto3
from botocore.config import Config

CONFIG = Config(connect_timeout=10, read_timeout=60, retries={"total_max_attempts": 1})

STATE = Path("deployment.json")


def save(state): STATE.write_text(json.dumps(state, indent=2)+"\n")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("stage", choices=["gateway", "runtime"])
    p.add_argument("--region", default="us-west-2")
    p.add_argument("--name", default="support_lab")
    p.add_argument("--lambda-role")
    p.add_argument("--gateway-role")
    p.add_argument("--runtime-role")
    p.add_argument("--image-uri")
    p.add_argument("--model-id")
    p.add_argument("--execute", action="store_true")
    a = p.parse_args()
    if not a.execute: p.error("Creation incurs AWS charges; supply --execute only after reviewing the deployment plan.")
    state = json.loads(STATE.read_text()) if STATE.exists() else {"region": a.region}
    if state["region"] != a.region: p.error("State region differs from requested region")
    control = boto3.client("bedrock-agentcore-control", region_name=a.region, config=CONFIG)
    if a.stage == "gateway":
        if not a.lambda_role or not a.gateway_role: p.error("Both --lambda-role and --gateway-role are required")
        if any(k in state for k in ["lambda_arn", "gateway_id"]): p.error("Partial/existing deployment found. Inspect deployment.json and resume manually; do not recreate blindly.")
        buf = io.BytesIO()
        with ZipFile(buf, "w") as z: z.write("tools_lambda.py", "tools_lambda.py")
        lam = boto3.client("lambda", region_name=a.region, config=CONFIG)
        function = lam.create_function(FunctionName=a.name+"_tools", Runtime="python3.12", Role=a.lambda_role,
            Handler="tools_lambda.handler", Code={"ZipFile": buf.getvalue()}, Timeout=15, MemorySize=128)
        state["lambda_arn"] = function["FunctionArn"]; save(state)
        lam.get_waiter("function_active_v2").wait(FunctionName=state["lambda_arn"])
        gateway = control.create_gateway(name=a.name.replace("_", "-"), roleArn=a.gateway_role, protocolType="MCP", authorizerType="AWS_IAM")
        state.update(gateway_id=gateway["gatewayId"], gateway_arn=gateway["gatewayArn"], gateway_url=gateway["gatewayUrl"]); save(state)
        for _ in range(30):
            status = control.get_gateway(gatewayIdentifier=state["gateway_id"])["status"]
            if status == "READY": break
            if status == "FAILED": raise RuntimeError("Gateway creation failed; inspect AWS status")
            time.sleep(2)
        else: raise TimeoutError("Gateway not ready; preserve state and inspect AWS")
        schema = {"type": "object", "properties": {"record_id": {"type": "string"}, "invocation_id": {"type": "string"}}, "required": ["record_id", "invocation_id"]}
        target = control.create_gateway_target(gatewayIdentifier=state["gateway_id"], name="support",
            targetConfiguration={"mcp": {"lambda": {"lambdaArn": state["lambda_arn"], "toolSchema": {"inlinePayload": [
                {"name": "lookup_customer", "description": "Read customer C-100", "inputSchema": schema},
                {"name": "lookup_ticket", "description": "Read ticket T-100", "inputSchema": schema}]}}}},
            credentialProviderConfigurations=[{"credentialProviderType": "GATEWAY_IAM_ROLE"}])
        state["target_id"] = target["targetId"]; save(state)
        print("Gateway stage created. Wait for target READY; grant runtime role InvokeGateway on gateway_arn before runtime stage.")
    else:
        if not all([a.runtime_role, a.image_uri, a.model_id]): p.error("--runtime-role, --image-uri and --model-id are required")
        if "gateway_url" not in state: p.error("Complete the gateway stage first")
        if "runtime_arn" in state: p.error("Runtime already recorded; inspect it rather than creating a duplicate")
        runtime = control.create_agent_runtime(agentRuntimeName=a.name,
            agentRuntimeArtifact={"containerConfiguration": {"containerUri": a.image_uri}},
            roleArn=a.runtime_role, networkConfiguration={"networkMode": "PUBLIC"},
            lifecycleConfiguration={"idleRuntimeSessionTimeout": 60, "maxLifetime": 180},
            environmentVariables={"GATEWAY_URL": state["gateway_url"], "BEDROCK_MODEL_ID": a.model_id, "AWS_REGION": a.region})
        state.update(runtime_arn=runtime["agentRuntimeArn"], runtime_id=runtime["agentRuntimeId"], model_id=a.model_id, image_uri=a.image_uri); save(state)
        print("Runtime creation requested. Wait for READY before invoking. Resource IDs are in deployment.json.")


if __name__ == "__main__": main()
