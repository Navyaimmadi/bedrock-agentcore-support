import os
import boto3
from botocore.config import Config
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from gateway_client import GatewayClient
from workflow import run_workflow

app = BedrockAgentCoreApp()


@app.entrypoint
def invoke(payload):
    region = os.environ.get("AWS_REGION", "us-west-2")
    model = os.environ["BEDROCK_MODEL_ID"]
    gateway = GatewayClient(os.environ["GATEWAY_URL"], region)
    client = boto3.client("bedrock-runtime", region_name=region,
                          config=Config(connect_timeout=10, read_timeout=60, retries={"total_max_attempts": 1}))
    return run_workflow(payload.get("prompt"), client.converse, gateway, model, count_tokens=client.count_tokens)


if __name__ == "__main__": app.run()
