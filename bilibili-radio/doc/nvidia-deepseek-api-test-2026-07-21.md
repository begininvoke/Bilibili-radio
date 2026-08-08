# NVIDIA DeepSeek API Test - 2026-07-21

## Scope

Tested NVIDIA OpenAI-compatible endpoint:

- Base URL: `https://integrate.api.nvidia.com/v1`
- SDK: `openai.OpenAI`
- API key: provided at runtime through environment variable, not written to project files

## Results

### Model Discovery

`GET /v1/models` succeeded.

- HTTP status: `200`
- Model count returned: `118`
- DeepSeek models found:
  - `deepseek-ai/deepseek-coder-6.7b-instruct`
  - `deepseek-ai/deepseek-v4-flash`
  - `deepseek-ai/deepseek-v4-pro`

This confirms that the API key, base URL, and model name discovery are working.

### `deepseek-ai/deepseek-v4-pro`

Two minimal chat completion attempts were made.

- Attempt with SDK timeout `20s`: failed with `APITimeoutError: Request timed out.`
- Attempt with SDK timeout `120s`: failed after about `62s` with `APIConnectionError: Connection error.`

Conclusion: `deepseek-ai/deepseek-v4-pro` is listed by the API, but chat completion was not healthy during this test window.

### `deepseek-ai/deepseek-v4-flash`

Minimal chat completion succeeded.

- Clean ASCII prompt elapsed time: `1.6s`
- Response:

```text
The model connection is functioning correctly. No issues detected.
```

An earlier Chinese prompt also returned quickly, but the local PowerShell-to-Python stdin path converted Chinese text into question marks. That was a local encoding issue, not an API failure.

## Judgment

`deepseek-ai/deepseek-v4-flash` is usable from this environment.

`deepseek-ai/deepseek-v4-pro` should not be treated as production-ready here until a later retry succeeds consistently. The endpoint and credentials are valid, so the likely issue is specific to the `pro` inference path, capacity, routing, or transient serving stability.

## Follow-up

For this project, use `deepseek-ai/deepseek-v4-flash` as the current working NVIDIA model. If `pro` is required, add a health check with short timeout and fallback to `flash`.
