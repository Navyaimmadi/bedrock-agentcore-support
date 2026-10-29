# Architecture

Router, Customer and Ticket are logical agents in one Python container, not separate AgentCore runtimes. The application calls Bedrock Converse for routing and then for the selected specialist's tool choice. Each workflow allows at most two model requests; a CountTokens preflight, when supported, limits cumulative input to 4,096 tokens, and output is limited to 1,024 tokens (512 per request). The workflow fails closed on missing counts, usage, or the expected tool call. Token counting and service behavior for the proposed profile have not been tested against AWS.

The specialist selects a single permitted lookup. The application discovers its Gateway-qualified MCP name and uses SigV4 with temporary Runtime role credentials. Gateway uses IAM inbound authorization and its execution role for the Lambda target. Lambda validates the tool identity and permits only synthetic customer C-100 or ticket T-100. The tool result is returned directly; no extra model call generates the answer.

One invocation UUID links application start, handoff, model usage, tool call and completion to Lambda's tool event. This correlation is implemented and exercised with mocks; CloudWatch delivery and the actual Gateway/Lambda path need live evidence. The code avoids logging user prompts and credentials. Log access and retention still need review before publishing sanitized evidence.

Identity is a scoped service role and fixed synthetic record scope, not end-user identity or tenant isolation. Conversation memory, writes, production load testing, private networking and enterprise identity integration are outside this starter. MCP transport, cross-region model access, exact cost and deployed behavior remain unverified. AWS account access and deployed behavior remain unverified.
