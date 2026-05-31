/**
 * Configuration for the local-models extension.
 *
 * Each known server has its documented API endpoint.
 * We probe only to check reachability, then use the configured API.
 */

import { readFileSync } from "node:fs";
import { join } from "node:path";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type ApiType = "anthropic-messages" | "openai-completions";

export interface DiscoveredServer {
  name: string;
  providerName: string;
  baseUrl: string;
  api: ApiType;
  models: DiscoveredModel[];
  thinkingFormat?: string;
}

export interface DiscoveredModel {
  id: string;
  name?: string;
  reasoning: boolean;
  input: ("text" | "image")[];
  contextWindow: number;
  maxTokens: number;
  cost: { input: number; output: number; cacheRead: number; cacheWrite: number };
  compat?: Record<string, unknown>;
}

export interface LocalModelsConfig {
  /** Which known servers to enable. Empty = enable all. */
  enabledServers?: string[];
  /** Skip embedding/reranker models. */
  skipEmbeddingModels?: boolean;
  /** Fallback context window. */
  defaultContextWindow?: number;
  /** Fallback max output tokens. */
  defaultMaxTokens?: number;
  /** Auto-register without prompting. */
  autoEnable?: boolean;
  /** Per-server reachability probe timeout. */
  probeTimeout?: number;
  /** Additional custom servers. */
  customServers?: Array<{
    name: string;
    baseUrl: string;
    api: ApiType;
    modelsEndpoint: string;
  }>;
}

export const DEFAULT_CONFIG: LocalModelsConfig = {
  enabledServers: [],
  skipEmbeddingModels: true,
  defaultContextWindow: 128000,
  defaultMaxTokens: 16384,
  autoEnable: true,
  probeTimeout: 3000,
};

/** Known local model servers with their documented APIs. */
export const KNOWN_SERVERS: Array<{
  name: string;
  baseUrl: string;
  /** API to use for chat completions */
  api: ApiType;
  /** Endpoint to list models (for reachability + model discovery) */
  modelsEndpoint: string;
  /** Default thinking format for this server (e.g., "qwen-chat-template") */
  thinkingFormat: string | undefined;
  /** Provider-level compat overrides */
  compat?: Record<string, unknown>;
}> = [
  {
    name: "ollama",
    baseUrl: "http://localhost:11434",
    api: "openai-completions",
    modelsEndpoint: "/api/tags",
    thinkingFormat: "qwen",
  },
  {
    name: "lm-studio",
    baseUrl: "http://localhost:1234",
    api: "openai-completions",
    modelsEndpoint: "/v1/models",
    thinkingFormat: "openai",
  },
  {
    name: "omlx",
    baseUrl: "http://localhost:8000",
    api: "openai-completions",
    modelsEndpoint: "/v1/models",
    thinkingFormat: "qwen-chat-template",
  },
  {
    name: "vllm",
    baseUrl: "http://localhost:8001",
    api: "openai-completions",
    modelsEndpoint: "/v1/models",
    thinkingFormat: undefined,
  },
  {
    name: "sglang",
    baseUrl: "http://localhost:30000",
    api: "openai-completions",
    modelsEndpoint: "/v1/models",
    thinkingFormat: undefined,
  },
  {
    name: "tgi",
    baseUrl: "http://localhost:8080",
    api: "openai-completions",
    modelsEndpoint: "/v1/models",
    thinkingFormat: undefined,
  },
  {
    name: "koboldcpp",
    baseUrl: "http://localhost:5000",
    api: "openai-completions",
    modelsEndpoint: "/v1/models",
    thinkingFormat: undefined,
  },
  {
    name: "llamafile",
    baseUrl: "http://localhost:8081",
    api: "openai-completions",
    modelsEndpoint: "/v1/models",
    thinkingFormat: undefined,
  },
];

/** Embedding/reranker patterns to filter out */
const EMBEDDING_PATTERNS = [/embedding/i, /rerank/i, /reranker/i, /text-embedding/i, /embed/i, /bge/i, /nomic.*embed/i];

export function isLikelyChatModel(id: string): boolean {
  return !EMBEDDING_PATTERNS.some((p) => p.test(id)) && !id.startsWith("./") && !id.startsWith("/") && id.length >= 3;
}

export function inferReasoning(id: string, name?: string): boolean {
  const text = `${id} ${name ?? ""}`.toLowerCase();
  // Known reasoning model families (Qwen 2.5+, Claude Sonnet/Opus, o1/o3, Gemini Pro/Flash)
  return (
    /thinking|reason|deep.*think|o1|o3|claude.*sonnet|claude.*opus|gemini.*pro|gemini.*flash|qwen/i.test(text) ||
    /thinking|reason/i.test(name ?? "")
  );
}

// ---------------------------------------------------------------------------
// Config loader
// ---------------------------------------------------------------------------

function readSettingsJson(): Record<string, unknown> {
  try {
    const raw = readFileSync(join(process.env.HOME ?? "/tmp", ".pi", "agent", "settings.json"), "utf-8");
    return JSON.parse(raw);
  } catch {
    return {};
  }
}

export function loadConfig(): LocalModelsConfig {
  const settings = readSettingsJson();
  const localModels = (settings.localModels as Record<string, unknown>) ?? {};
  const config: LocalModelsConfig = { ...DEFAULT_CONFIG, ...localModels };
  if (!config.enabledServers || config.enabledServers.length === 0) {
    config.enabledServers = [];
  }
  return config;
}
