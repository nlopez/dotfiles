# pi-local-models

Auto-discovers local model servers and registers them as Pi providers.

## What it does

Probes common local model server endpoints (Ollama, LM Studio, vLLM, SGLang, TGI, KoboldCpp, llamafile) and automatically registers any running server as a Pi provider with all its models.

## Features

- **Auto-discovery** — probes 7 common local servers on startup
- **Reasoning detection** — probes each model with lightweight test requests to determine if extended thinking is supported
- **Auto-detect API type** — distinguishes Ollama (`/api/tags`) from OpenAI-compatible (`/v1/models`) servers
- **Embedding filter** — skips embedding/reranker models automatically
- **Manual refresh** — `/refresh-local-models` to re-discover after servers start/stop
- **Configurable** — all settings via `~/.pi/agent/settings.json` → `localModels` key

## Configuration

Add a `localModels` key to `~/.pi/agent/settings.json`:

```json
{
  "localModels": {
    "enabledServers": ["Ollama", "LM Studio"],
    "customServers": [
      {
        "name": "My Server",
        "baseUrl": "http://localhost:9000",
        "api": "openai-completions"
      }
    ],
    "skipEmbeddingModels": true,
    "defaultContextWindow": 128000,
    "defaultMaxTokens": 16384,
    "autoEnable": true,
    "probeTimeout": 3000
  }
}
```

### Options

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `enabledServers` | `string[]` | `[]` (all) | Which built-in servers to probe. Empty = probe all. |
| `customServers` | `Server[]` | `[]` | Additional servers to probe. |
| `customServers[].name` | `string` | — | Display name. |
| `customServers[].baseUrl` | `string` | — | Base URL (e.g., `http://localhost:8000`). |
| `customServers[].api` | `string` | `openai-completions` | API type (`openai-completions`, `anthropic-messages`, `openai-responses`, `google-generative-ai`). |
| `skipEmbeddingModels` | `boolean` | `true` | Skip models that look like embeddings/rerankers. |
| `defaultContextWindow` | `number` | `128000` | Fallback context window in tokens. |
| `defaultMaxTokens` | `number` | `16384` | Fallback max output tokens. |
| `autoEnable` | `boolean` | `true` | Auto-register discovered providers without prompting. |
| `probeTimeout` | `number` | `3000` | Timeout per server probe in milliseconds. |

## Built-in servers

| Name | Port | Endpoint |
|------|------|----------|
| Ollama | 11434 | `/api/tags` |
| LM Studio | 1234 | `/v1/models` |
| vLLM | 8000 | `/v1/models` |
| SGLang | 30000 | `/v1/models` |
| TGI | 8080 | `/v1/models` |
| KoboldCpp | 5000 | `/v1/models` |
| llamafile | 8081 | `/v1/models` |

## Commands

- `/refresh-local-models` — Re-probe all servers and update registered providers.

## How reasoning detection works

For each discovered model, the extension sends lightweight test requests with different reasoning/thinking formats:

1. `{ thinking: { type: "enabled" } }` — Ollama / generic
2. `{ reasoning: { effort: "minimal" } }` — OpenRouter / some providers
3. `{ enable_thinking: true }` — Qwen format
4. `{ chat_template_kwargs: { enable_thinking: true } }` — Qwen chat template

A model is marked as reasoning-capable if the server accepts the request (2xx) or returns a 400/422 error indicating it recognized the field.

## Files

```
local-models/
├── index.ts        # Extension entry point (async factory)
├── discover.ts     # Server probing and model discovery
├── providers.ts    # Provider config builders
├── config.ts       # Config loading, defaults, shared types
├── package.json    # Pi package metadata
└── README.md
```
