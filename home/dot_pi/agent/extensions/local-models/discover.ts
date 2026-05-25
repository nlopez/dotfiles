/**
 * Discovery logic: probe known servers for reachability + model lists.
 *
 * No API detection — each server has a pre-configured API from its docs.
 */

import type { DiscoveredModel, DiscoveredServer, LocalModelsConfig } from "./config";
import { KNOWN_SERVERS, DEFAULT_CONFIG, isLikelyChatModel, inferReasoning } from "./config";

// ---------------------------------------------------------------------------
// Response types
// ---------------------------------------------------------------------------

interface OpenAIModelsResponse {
  object: string;
  data: Array<{ id: string; name?: string }>;
}

interface OllamaTagsResponse {
  models: Array<{ name: string; model: string }>;
}

// ---------------------------------------------------------------------------
// Probe a single known server
// ---------------------------------------------------------------------------

interface ProbeResult {
  name: string;
  providerName: string;
  baseUrl: string;
  api: "openai-completions" | "anthropic-messages";
  models: DiscoveredModel[];
  thinkingFormat: string | undefined;
  compat: Record<string, unknown> | undefined;
}

/** Check reachability and fetch model list from a server. */
async function probeServer(
  server: (typeof KNOWN_SERVERS)[number],
  config: LocalModelsConfig
): Promise<ProbeResult | null> {
  const url = `${server.baseUrl}${server.modelsEndpoint}`;
  const timeout = config.probeTimeout ?? DEFAULT_CONFIG.probeTimeout;

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeout);

  try {
    const response = await fetch(url, {
      signal: controller.signal,
      headers: { Accept: "application/json" },
    });

    if (!response.ok) return null;

    // Parse model list based on endpoint type
    const data = await response.json();
    let modelIds: Array<{ id: string; name?: string }> = [];

    if (server.modelsEndpoint === "/api/tags") {
      // Ollama format
      const ollama = data as OllamaTagsResponse;
      if (!ollama.models) return null;
      modelIds = ollama.models.map((m) => ({ id: m.model, name: m.name }));
    } else {
      // OpenAI / Anthropic / generic format
      const openai = data as OpenAIModelsResponse;
      if (!openai.data) return null;
      modelIds = openai.data;
    }

    const models = modelIds
      .filter((m) => isLikelyChatModel(m.id))
      .map((m) => ({
        id: m.id,
        name: m.name,
        reasoning: false,
        input: ["text"] as const,
        contextWindow: config.defaultContextWindow ?? DEFAULT_CONFIG.defaultContextWindow,
        maxTokens: config.defaultMaxTokens ?? DEFAULT_CONFIG.defaultMaxTokens,
        cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0 },
      }));

    const providerName = `local-${server.name}`;

    return {
      name: server.name,
      providerName,
      baseUrl: server.baseUrl,
      api: server.api,
      models,
      thinkingFormat: server.thinkingFormat,
      compat: server.compat,
    };
  } catch {
    return null;
  } finally {
    clearTimeout(timer);
  }
}

// ---------------------------------------------------------------------------
// Infer reasoning support from model IDs (no network probe needed)
// ---------------------------------------------------------------------------

function markReasoning(models: DiscoveredModel[]): DiscoveredModel[] {
  return models.map((m) => ({
    ...m,
    reasoning: inferReasoning(m.id, m.name),
  }));
}

// ---------------------------------------------------------------------------
// Main discovery
// ---------------------------------------------------------------------------

export async function discoverServers(
  config: LocalModelsConfig
): Promise<DiscoveredServer[]> {
  const results: DiscoveredServer[] = [];

  // Filter to enabled servers
  const enabled = KNOWN_SERVERS.filter((s) => {
    if (config.enabledServers.length === 0) return true;
    return config.enabledServers.includes(s.name);
  });

  // Probe all in parallel
  const probes = await Promise.all(
    enabled.map((s) => probeServer(s, config))
  );

  for (const r of probes) {
    if (!r) continue;

    // Mark reasoning support from model IDs
    const models = markReasoning(r.models);

    results.push({
      name: r.name,
      providerName: r.providerName,
      baseUrl: r.baseUrl,
      api: r.api,
      models,
    });
  }

  return results;
}
