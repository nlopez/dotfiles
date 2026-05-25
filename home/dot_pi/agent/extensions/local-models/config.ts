/**
 * Configuration loader for the local-models extension.
 *
 * Reads from ~/.pi/agent/settings.json under the "localModels" key.
 * Falls back to sensible defaults if not configured.
 */

import { readFileSync } from "node:fs";
import { join } from "node:path";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface DiscoveredServer {
  /** Display name shown in UI */
  name: string;
  /** Provider name registered with pi */
  providerName: string;
  /** Base URL of the server */
  baseUrl: string;
  /** API type detected or configured */
  api: "openai-completions" | "anthropic-messages" | "openai-responses" | "google-generative-ai";
  /** Detected or default model list */
  models: DiscoveredModel[];
}

export interface DiscoveredModel {
  id: string;
  name?: string;
  reasoning: boolean;
  input: ("text" | "image")[];
  contextWindow: number;
  maxTokens: number;
  cost: { input: number; output: number; cacheRead: number; cacheWrite: number };
  /** Compatibility overrides for this model */
  compat?: Record<string, unknown>;
}

/** User-facing configuration from settings.json */
export interface LocalModelsConfig {
  /** Which built-in servers to probe. Empty = probe all. */
  enabledServers?: string[];
  /** Additional custom servers to probe. */
  customServers?: Array<{
    name: string;
    baseUrl: string;
    api?: "openai-completions" | "anthropic-messages" | "openai-responses" | "google-generative-ai";
  }>;
  /** Skip models that look like embeddings/rerankers. Default: true */
  skipEmbeddingModels?: boolean;
  /** Default context window when the server doesn't report it. */
  defaultContextWindow?: number;
  /** Default max output tokens. */
  defaultMaxTokens?: number;
  /** Auto-register discovered providers without prompting. Default: true */
  autoEnable?: boolean;
  /** Probe timeout per server in ms. Default: 3000 */
  probeTimeout?: number;
}

/** Default configuration */
export const DEFAULT_CONFIG: LocalModelsConfig = {
  enabledServers: [], // empty = probe all
  skipEmbeddingModels: true,
  defaultContextWindow: 128000,
  defaultMaxTokens: 16384,
  autoEnable: true,
  probeTimeout: 3000,
};

/** Built-in servers to probe, in order */
export const BUILTIN_SERVERS: Array<{
  name: string;
  baseUrl: string;
  api: "openai-completions" | "anthropic-messages";
  endpoint: string;
}> = [
  { name: "Ollama", baseUrl: "http://localhost:11434", api: "openai-completions", endpoint: "/api/tags" },
  { name: "LM Studio", baseUrl: "http://localhost:1234", api: "openai-completions", endpoint: "/v1/models" },
  { name: "vLLM", baseUrl: "http://localhost:8000", api: "openai-completions", endpoint: "/v1/models" },
  { name: "SGLang", baseUrl: "http://localhost:30000", api: "openai-completions", endpoint: "/v1/models" },
  { name: "TGI", baseUrl: "http://localhost:8080", api: "openai-completions", endpoint: "/v1/models" },
  { name: "KoboldCpp", baseUrl: "http://localhost:5000", api: "openai-completions", endpoint: "/v1/models" },
  { name: "llamafile", baseUrl: "http://localhost:8081", api: "openai-completions", endpoint: "/v1/models" },
];

/** Embedding/reranker model ID patterns to skip */
const EMBEDDING_PATTERNS = [
  /embedding/i,
  /rerank/i,
  /reranker/i,
  /text-embedding/i,
  /embed/i,
  /bge/i,
  /nomic.*embed/i,
];

/** Heuristic: does this model ID look like a chat model? */
export function isLikelyChatModel(id: string): boolean {
  if (EMBEDDING_PATTERNS.some((p) => p.test(id))) return false;
  // Skip if it's clearly not a model (e.g., directory-like paths)
  if (id.startsWith("./") || id.startsWith("/")) return false;
  // Very short IDs are suspicious
  if (id.length < 3) return false;
  return true;
}

/** Heuristic: does this model ID suggest reasoning support? */
export function inferReasoning(id: string, name?: string): boolean {
  const combined = `${id} ${name ?? ""}`.toLowerCase();
  return (
    /thinking|reason|deep.*think|o1|o3|claude.*sonnet|claude.*opus|gemini.*pro|gemini.*flash|qwen.*think|qwen.*reason/i.test(
      combined
    ) ||
    /thinking|reason/i.test(name ?? "")
  );
}

// ---------------------------------------------------------------------------
// Load config from settings.json
// ---------------------------------------------------------------------------

function readSettingsJson(): Record<string, unknown> {
  const settingsPath = join(process.env.HOME ?? "/tmp", ".pi", "agent", "settings.json");
  try {
    const raw = readFileSync(settingsPath, "utf-8");
    return JSON.parse(raw);
  } catch {
    return {};
  }
}

export function loadConfig(): LocalModelsConfig {
  const settings = readSettingsJson();
  const localModels = (settings.localModels as Record<string, unknown>) ?? {};

  const config: LocalModelsConfig = {
    ...DEFAULT_CONFIG,
    ...localModels,
  };

  // Merge enabledServers: empty array means "all"
  if (!config.enabledServers || config.enabledServers.length === 0) {
    config.enabledServers = []; // signal to probe all
  }

  return config;
}
