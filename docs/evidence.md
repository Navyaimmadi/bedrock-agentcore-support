# Evidence and acceptance checklist

Offline tests and the local `/ping` health check are not evidence of deployment, model inference, MCP, Lambda through Gateway, or CloudWatch delivery. Do not publish a claim of completion until each item below is supported by real, sanitized evidence.

- [ ] Record the actual date, account (redacted in public artifacts), region, image digest, model/profile ID and destination regions, and describe any SCP or plan limitation.
- [ ] Capture read-only Gateway, target and Runtime status showing READY after deployment. Preserve deployment.json privately; do not commit it.
- [ ] Run the one-shot verification coordinator once. Retain both result records and invocation IDs; it stops on the first failed or unexpected response. A timeout is ambiguous and must not be retried without offline diagnosis before any retry.
- [ ] For each invocation, collect matching Runtime events `invocation_started`, `handoff`, `tool_started`, `tool_completed`, `invocation_completed`, and model usage; collect the matching Lambda `tool_executed` event and tool name. Verify the returned specialist and fixed record. Review whether available Gateway logs independently confirm the MCP path. The coordinator does not inspect logs between its two calls.
- [ ] Record actual permissions and evidence that Gateway uses IAM inbound authorization, its role invokes only the lab Lambda, and Runtime uses the specified model/profile and Gateway. Explain the fixed-record identity limitation.
- [ ] Save sanitized outputs and correlated events in `outputs/live/`, excluding credentials, account identifiers and sensitive prompts. Keep exact IDs and raw state private. No invented screenshots, usage, costs, or status.
- [ ] Review source and logs for credentials, check links, and prepare source, lockfile, architecture and sanitized evidence for submission.

After deployment, discover the actual Runtime and Lambda log groups in CloudWatch. For each group and invocation ID, an example read-only log query is:

```bash
aws logs filter-log-events --region us-east-2 --log-group-name "$LOG_GROUP" --filter-pattern '"'"$INVOCATION_ID"'"' --no-cli-pager
```

Confirm the group belongs to this lab before reading or deleting it. Avoid exporting unrelated events. Retention and cleanup follow [deployment.md](deployment.md).
