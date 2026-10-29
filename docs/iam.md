# Least-privilege IAM setup

This is a scoped lab design, not an observed effective policy. Review account access and resource-specific permissions before deploying. Use dedicated roles; do not attach AdministratorAccess or alter organization policies. The exact policy documents depend on the real resource ARNs and must be reviewed before creation. A role policy cannot override an SCP.

| Identity | Trust | Required scope |
| --- | --- | --- |
| Operator | Existing authenticated identity | Create/read lab IAM roles, Lambda, Gateway, Runtime, ECR and log resources; `iam:PassRole` only for the three lab roles and intended services. Invocation and cleanup permissions are needed for their respective stages. |
| Lambda role | `lambda.amazonaws.com` | Create/write the dedicated Lambda log group and streams; no Bedrock or data store access. |
| Gateway role | `bedrock-agentcore.amazonaws.com` | `lambda:InvokeFunction` on the exact lab Lambda ARN; account for `bedrock-agentcore:InvokeGateway` on the actual gateway ARN as required by AWS outbound IAM guidance. |
| Runtime role | `bedrock-agentcore.amazonaws.com` | Gateway invoke on its exact ARN; Bedrock CountTokens and InvokeModel for the chosen profile and associated foundation models, ECR pull and Runtime logging/telemetry. |
| Invocation operator | Existing authenticated identity | `bedrock-agentcore:InvokeAgentRuntime` on the Runtime and applicable endpoint resources. |

## Trust policies

Use the AWS documented trust conditions `aws:SourceAccount` and `aws:SourceArn`. For Runtime, use the actual account, region and Runtime ARN pattern described in the [Runtime execution-role reference](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-permissions.html). For Gateway, use the dedicated gateway name pattern initially, then tighten to its actual ARN after creation; see [Gateway service role permissions](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway-prerequisites-permissions.html). Lambda trusts `lambda.amazonaws.com`. Do not assume conditions work for a service without reviewing its official trust requirements.

## Runtime policy scope

- `bedrock-agentcore:InvokeGateway`: exact Gateway ARN after creation.
- `bedrock:InvokeModel`: exact inference-profile ARN in us-east-2, plus the three destination foundation-model ARNs returned by GetInferenceProfile. AWS recommends `bedrock:InferenceProfileArn` on the foundation-model statement to constrain invocation through that profile. A deny in any destination SCP can prevent cross-region inference. See [profile permissions](https://docs.aws.amazon.com/bedrock/latest/userguide/inference-profiles-prereq.html).
- `bedrock:CountTokens`: authorize the action for the resources supported by the service authorization reference and tested API configuration. The exact profile support and necessary resource scope are unresolved; do not replace a denied or unsupported preflight with an inference call.
- `ecr:BatchGetImage` and `ecr:GetDownloadUrlForLayer`: exact repository ARN; `ecr:GetAuthorizationToken` requires `Resource: "*"`.
- Runtime log permissions and applicable X-Ray/CloudWatch telemetry: follow the current [Runtime execution-role reference](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-permissions.html), limiting resources and metric namespace where supported. The official example includes `logs:DescribeLogGroups`, `logs:CreateLogGroup`, `logs:DescribeLogStreams`, `logs:CreateLogStream`, and `logs:PutLogEvents`, with additional telemetry actions. Do not enable account-wide Transaction Search merely to satisfy the lab's application log evidence.

For Gateway `GATEWAY_IAM_ROLE`, review both [Gateway role permissions](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway-prerequisites-permissions.html) and [outbound IAM authorization](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway-outbound-auth.html). Attach the exact Lambda function ARN, and scope gateway permissions to the recorded gateway ARN. Caller identity needs its own `bedrock-agentcore:InvokeGateway` grant. The Runtime authenticates as a service identity, not as an end user; fixed synthetic records are not tenant isolation.

Create each role using `aws iam create-role --role-name ROLE_NAME --assume-role-policy-document file://TRUST_FILE` and attach a reviewed inline policy with `aws iam put-role-policy --role-name ROLE_NAME --policy-name POLICY_NAME --policy-document file://POLICY_FILE`. Store sanitized policy files and record their names. Follow [deployment.md](deployment.md) for resource sequencing and [deployment.md](deployment.md) for cleanup.
