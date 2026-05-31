/**
 * Configuration for the local-models extension.
 * Supports: omlx, lm-studio
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
  /** Full API base URL including /v1 — passed directly to pi.registerProvider */
  baseUrl: string;
  api: ApiType;
  models: DiscoveredModel[];
  thinkingFormat?: string;
  /** API key for both probe requests and registered provider */
  apiKey: string;
  /** Whether to send Authorization: Bearer {apiKey} header */
  authHeader?: boolean;
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
  enabledServers?: string[];
  skipEmbeddingModels?: boolean;
  defaultContextWindow?: number;
  defaultMaxTokens?: number;
  autoEnable?: boolean;
  probeTimeout?: number;
}

export const DEFAULT_CONFIG: Required<LocalModelsConfig> = {
  enabledServers: [],
  skipEmbeddingModels: true,
  defaultContextWindow: 128000,
  defaultMaxTokens: 16384,
  autoEnable: true,
  probeTimeout: 3000,
};

/**
 * Known servers.
 *
 * baseUrl must include /v1 — Pi appends /chat/completions directly to it.
 * modelsEndpoint is relative to baseUrl (e.g. "/models" → baseUrl + "/models").
 */
export const KNOWN_SERVERS: Array<{
  name: string;
  /** Full API base URL including /v1 */
  baseUrl: string;
  api: ApiType;
  /** Path relative to baseUrl used to list models */
  modelsEndpoint: string;
  thinkingFormat: string | undefined;
  compat?: Record<string, unknown>;
  apiKey: string;
  authHeader?: boolean;
}> = [
  {
    name: "omlx",
    baseUrl: "http://localhost:8000/v1",
    api: "openai-completions",
    modelsEndpoint: "/models",
    thinkingFormat: "qwen-chat-template",
    apiKey: "omlx-kdc8uke8vsvje15d",
    authHeader: true,
  },
  {
    name: "lm-studio",
    baseUrl: "http://localhost:1234/v1",
    api: "openai-completions",
    modelsEndpoint: "/models",
    thinkingFormat: "openai",
    apiKey: "lm-studio",
    authHeader: false,
  },
];

// ---------------------------------------------------------------------------
// Model filtering
// ---------------------------------------------------------------------------

const EMBEDDING_PATTERNS = [/embedding/i, /rerank/i, /reranker/i, /text-embedding/i, /embed/i, /bge/i, /nomic.*embed/i];

export function isLikelyChatModel(id: string): boolean {
  return !EMBEDDING_PATTERNS.some((p) => p.test(id)) && !id.startsWith("./") && !id.startsWith("/") && id.length >= 3;
}

export function inferReasoning(id: string, name?: string): boolean {
  const text = `${id} ${name ?? ""}`.toLowerCase();
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
