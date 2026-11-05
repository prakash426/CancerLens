# Live Meta text call receipt

Date: 29 Oct 2026 (UTC)
Gate: TESTING.md Gate 1, provider check
Model: muse-spark-1.3
Endpoint: POST https://api.meta.ai/v1/responses

## Request (redacted)

Headers:

* Authorization: Bearer [REDACTED]
* Content-Type: application/json

Body:

```json
{"model": "muse-spark-1.3", "input": "What is the capital of France?"}
```

The key was supplied from the server side environment at call time and is not stored in this repo.

## Result

* Status: completed
* Response id: resp_6ae2e2f2c758d7404e6a40f0
* Assistant text: The capital of France is Paris!
* Usage: 15 input tokens, 261 output tokens, 276 total
* Error: null

Full response body (contains no secrets):

```json
{
  "id": "resp_6ae2e2f2c758d7404e6a40f0",
  "object": "response",
  "status": "completed",
  "model": "muse-spark-1.3",
  "created_at": 1793254130.0,
  "completed_at": 1793254130.0,
  "error": null,
  "incomplete_details": null,
  "output": [
    {
      "type": "reasoning",
      "id": "rs_6ae2e2f2c758d7404e6a40f0:rs_5ab191b7-4b3a-4e69-b739-633ee007c243",
      "summary": [],
      "status": "completed"
    },
    {
      "type": "message",
      "id": "msg_07bf5b56-05eb-48cf-a76d-13325c8937c7",
      "role": "assistant",
      "content": [
        {
          "type": "output_text",
          "text": "The capital of France is Paris!",
          "annotations": [],
          "logprobs": []
        }
      ],
      "status": "completed"
    }
  ],
  "usage": {
    "input_tokens": 15,
    "input_tokens_details": {"cached_tokens": 0},
    "output_tokens": 261,
    "output_tokens_details": {"reasoning_tokens": 245},
    "total_tokens": 276
  },
  "temperature": 1.0,
  "top_p": 1.0,
  "top_logprobs": 0,
  "service_tier": "auto",
  "reasoning": {"effort": "high"},
  "background": false,
  "tools": [],
  "tool_choice": "auto",
  "parallel_tool_calls": true,
  "truncation": "disabled",
  "store": true,
  "instructions": null
}
```

## What this proves, and what stays open

Proves: authenticated text call works, model id matches, response structure and usage fields are present.
Stays open: pricing, structured response support, retention policy, and model access review, per ARCHITECTURE.md. A separate pricing check is still needed.
