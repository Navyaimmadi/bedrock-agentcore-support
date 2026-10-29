# Deployment guide

AWS deployment remains pending account access and has not been tested. Resource creation and inference incur usage charges. Confirm account permissions, region support, model entitlement and applicable pricing before proceeding. The candidate region is `us-east-2`; the candidate inference profile is `us.amazon.nova-micro-v1:0`. Cross-region inference requires permission for all profile destinations. `CountTokens` support for this exact profile remains unverified; the application fails closed if token counting fails.

The deployment uses a private ECR image repository, separate Lambda, Gateway and Runtime roles, one Lambda function, one Gateway with a two-tool target, one Runtime and CloudWatch logs. Review [IAM](iam.md). The script does not create IAM roles or the ECR repository. The image must be built for `linux/arm64`:

```bash
docker buildx build --platform linux/arm64 --provenance=false --load -t support-agentcore-lab:latest .
```

Create a dedicated private repository and push the image using the verified account and region. Supply the Lambda and Gateway role ARNs:

```bash
.venv/bin/python deploy.py gateway --execute --region us-east-2 --lambda-role "$LAMBDA_ROLE_ARN" --gateway-role "$GATEWAY_ROLE_ARN"
```

Inspect `deployment.json`, wait for the Gateway target to reach READY, and restrict the Runtime role to the recorded Gateway ARN. Then create the Runtime with the actual Runtime role and image URI:

```bash
.venv/bin/python deploy.py runtime --execute --region us-east-2 --runtime-role "$RUNTIME_ROLE_ARN" --image-uri "$ECR_IMAGE_URI" --model-id us.amazon.nova-micro-v1:0
```

Wait for Runtime READY. The script records resource identifiers after each create; preserve `deployment.json` if a step fails. It does not roll back partial resources. Do not blindly repeat creation. The Runtime sets a 60-second idle timeout and 180-second maximum instance lifetime.

The one-shot `verify_live.py` coordinator runs a customer request followed by a ticket request, stops on the first failure and preserves a journal. It makes at most four model requests across the two workflows. See [evidence.md](evidence.md) for the outstanding live acceptance checks. Before inference, establish explicit usage and cost limits; a timeout does not necessarily cancel server-side work.

## Cleanup

After deciding to tear down the lab, inspect `deployment.json` and substitute actual identifiers in these commands. Wait for each asynchronous deletion to complete and do not delete shared resources:

```bash
aws bedrock-agentcore-control delete-gateway-target --region us-east-2 --gateway-identifier "$GATEWAY_ID" --target-id "$TARGET_ID"
aws bedrock-agentcore-control delete-gateway --region us-east-2 --gateway-identifier "$GATEWAY_ID"
aws bedrock-agentcore-control delete-agent-runtime --region us-east-2 --agent-runtime-id "$RUNTIME_ID"
aws lambda delete-function --region us-east-2 --function-name "$LAMBDA_ARN"
aws ecr delete-repository --region us-east-2 --repository-name "$REPOSITORY" --force
```

The last command deletes all images in that repository. Then inspect and remove only lab-owned role policies and roles, and delete only the lab log groups using `aws logs delete-log-group --region us-east-2 --log-group-name "$LOG_GROUP"`. Verify deletion and review billing; ECR images and retained logs can continue to accrue charges.

References: [Runtime permissions](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-permissions.html), [Gateway setup](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway-create-api.html), [AgentCore pricing](https://aws.amazon.com/bedrock/agentcore/pricing/).
