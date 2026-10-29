# Local verification evidence

On October 28, 2026, Python 3.12.4 ran:

```text
python -m unittest discover -s tests -v
Ran 6 tests
OK
```

The tests use model and Gateway doubles. They cover both routes, scope denial, missing tool use, invalid input, the cumulative usage threshold, and token-preflight rejection. No model inference or AWS API calls were made.

A local Docker image was built for `linux/arm64`. Inspection reported 301,167,021 bytes. After a short startup wait, an HTTP request to `/ping` returned `200 OK` and `{"status":"Healthy"}`. The local container was removed. This establishes local startup only; it does not verify deployment, Gateway transport, cloud logging, or model access.
