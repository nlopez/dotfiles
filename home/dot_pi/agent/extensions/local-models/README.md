# pi-local-models

Auto-discovers local model servers and registers them as Pi providers.

## How it works

Each known server has a pre-configured API based on its documentation.
The extension probes only for reachability (GET to the models endpoint)
and uses the documented API for chat completions.

## Known servers

| Name | Port | API | Models endpoint |
|------|------|-----|-----------------|
| ollama | 11434 | openai-completions | `/api/tags` |
| lm-studio | 1234 | **anthropic-messages** | `/v1/messages` |
| vllm | 8000 | openai-completions | `/v1/models` |
| sglang | 30000 | openai-completions | `/v1/models` |
| tgi | 8080 | openai-completions | `/v1/models` |
| koboldcpp | 5000 | openai-completions | `/v1/models` |
| llamafile | 8081 | openai-completions | `/v1/models` |

## Configuration

Add a `localModels` key to `~/.pi/agent/settings.json`:

```json
{
  "localModels": {
    "enabledServers": ["ollama", "lm-studio"],
    "skipEmbeddingModels": true,
    "defaultContextWindow": 128000,
    "defaultMaxTokens": 16384,
    "autoEnable": true,
    "probeTimeout": 3000,
    "customServers": [
      {
        "name": "my-server",
        "baseUrl": "http://localhost:9000",
        "api": "anthropic-messages",
        "modelsEndpoint": "/v1/messages"
      }
    ]
  }
}
```

### Options

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `enabledServers` | `string[]` | `[]` (all) | Which known servers to enable |
| `customServers` | `Server[]` | `[]` | Additional servers to probe |
| `skipEmbeddingModels` | `boolean` | `true` | Skip embedding/reranker models |
| `defaultContextWindow` | `number` | `128000` | Fallback context window |
| `defaultMaxTokens` | `number` | `16384` | Fallback max output tokens |
| `autoEnable` | `boolean` | `true` | Auto-register without prompting |
| `probeTimeout` | `number` | `3000` | Per-server probe timeout (ms) |

## Commands

- `/refresh-local-models` — Re-probe all servers and update providers

## Reasoning detection

Reasoning support is inferred from model ID heuristics (contains "thinking", "reason", "qwen", etc.).
No network probing is needed.

## Files

```
local-models/
├── index.ts        # Extension entry point (async factory)
├── discover.ts     # Reachability probe + model list parsing
├── providers.ts    # ProviderConfig builders
├── config.ts       # Known servers, defaults, shared types
├── package.json    # Pi package metadata
└── README.md
```
