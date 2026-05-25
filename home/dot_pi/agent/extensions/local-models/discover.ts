/**
 * Discovery logic for local model servers.
 *
 * Probes known endpoints, parses responses, and returns discovered models.
 */

import type { DiscoveredModel, DiscoveredServer, LocalModelsConfig } from "./config";
import { BUILTIN_SERVERS, DEFAULT_CONFIG, inferReasoning, isLikelyChatModel } from "./config";

// ---------------------------------------------------------------------------
// Response types from various servers
// ---------------------------------------------------------------------------

interface OpenAIModelsResponse {
  object: string;
  data: Array<{
    id: string;
    object?: string;
    created?: number;
    owned_by?: string;
    name?: string;
    id_list?: string[];
  }>;
}

interface OllamaTagsResponse {
  models: Array<{
    name: string;
    model: string;
    modified_at: string;
    size: number;
    digest: string;
    details?: {
      parent_model?: string;
      format?: string;
      family?: string;
      families?: string[];
      parameter_size?: string;
      quantization_level?: string;
    };
  }>;
}

// ---------------------------------------------------------------------------
// Probe a single server
// ---------------------------------------------------------------------------

interface ProbeResult {
  name: string;
  baseUrl: string;
  api: "openai-completions" | "anthropic-messages";
  models: DiscoveredModel[];
  /** Whether reasoning support was actually probed */
  reasoningProbed: boolean;
}

async function probeOpenAICompatible(
  name: string,
  baseUrl: string,
  endpoint: string,
  config: LocalModelsConfig
): Promise<ProbeResult | null> {
  const url = `${baseUrl}${endpoint}`;
  const timeout = config.probeTimeout ?? DEFAULT_CONFIG.probeTimeout;

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeout);

  try {
    const response = await fetch(url, {
      signal: controller.signal,
      headers: { Accept: "application/json" },
    });

    if (!response.ok) return null;

    const data = (await response.json()) as OpenAIModelsResponse;
    if (!data.data || !Array.isArray(data.data)) return null;

    const models = data.data
      .map((m) => m.id)
      .filter((id) => isLikelyChatModel(id))
      .map((id) => {
        const found = data.data.find((d) => d.id === id);
        return {
          id,
          name: found?.name ?? undefined,
          reasoning: false, // will be probed separately
          input: ["text"],
          contextWindow: config.defaultContextWindow ?? DEFAULT_CONFIG.defaultContextWindow,
          maxTokens: config.defaultMaxTokens ?? DEFAULT_CONFIG.defaultMaxTokens,
          cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0 },
        };
      });

    return { name, baseUrl, api: "openai-completions", models, reasoningProbed: false };
  } catch {
    return null;
  } finally {
    clearTimeout(timer);
  }
}

async function probeOllama(
  name: string,
  baseUrl: string,
  config: LocalModelsConfig
): Promise<ProbeResult | null> {
  const url = `${baseUrl}/api/tags`;
  const timeout = config.probeTimeout ?? DEFAULT_CONFIG.probeTimeout;

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeout);

  try {
    const response = await fetch(url, {
      signal: controller.signal,
      headers: { Accept: "application/json" },
    });

    if (!response.ok) return null;

    const data = (await response.json()) as OllamaTagsResponse;
    if (!data.models || !Array.isArray(data.models)) return null;

    const models = data.models
      .map((m) => m.model)
      .filter((id) => isLikelyChatModel(id))
      .map((id) => {
        const found = data.models.find((m) => m.model === id);
        return {
          id,
          name: found?.name ?? id,
          reasoning: false, // will be probed separately
          input: ["text"],
          contextWindow: config.defaultContextWindow ?? DEFAULT_CONFIG.defaultContextWindow,
          maxTokens: config.defaultMaxTokens ?? DEFAULT_CONFIG.defaultMaxTokens,
          cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0 },
        };
      });

    return { name, baseUrl, api: "openai-completions", models, reasoningProbed: false };
  } catch {
    return null;
  } finally {
    clearTimeout(timer);
  }
}

// ---------------------------------------------------------------------------
// Probe reasoning support via a lightweight test request
// ---------------------------------------------------------------------------

async function probeReasoningSupport(
  baseUrl: string,
  modelId: string,
  api: string,
  timeout: number
): Promise<boolean> {
  const probeTimeout = Math.min(timeout, 1000); // Cap at 1s per model

  // Try thinking format for OpenAI-compatible servers
  const thinkingFormats = [
    { thinking: { type: "enabled" } }, // Ollama / generic
    { reasoning: { effort: "minimal" } }, // OpenRouter / some providers
    { enable_thinking: true }, // Qwen format
    { chat_template_kwargs: { enable_thinking: true } }, // Qwen chat template
  ];

  for (const body of thinkingFormats) {
    try {
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), probeTimeout);

      const response = await fetch(`${baseUrl}/v1/chat/completions`, {
        method: "POST",
        signal: controller.signal,
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
        },
        body: JSON.stringify({
          model: modelId,
          messages: [{ role: "user", content: "say hi" }],
          max_tokens: 10,
          stream: false,
          ...body,
        }),
      });

      clearTimeout(timer);

      // Accept 200 (success) or 400/422 with specific error patterns
      // that indicate the format is recognized but params are wrong
      if (response.ok) return true;

      const text = await response.text();
      // If the error mentions something other than thinking/reasoning,
      // the server at least recognized the field
      if (
        response.status === 400 ||
        response.status === 422 ||
        /thinking|reason|unsupported.*format/i.test(text)
      ) {
        return true;
      }
    } catch {
      // Timeout or network error — move to next format
    }
  }

  return false;
}

// ---------------------------------------------------------------------------
// Batch reasoning probes (limited concurrency)
// ---------------------------------------------------------------------------

async function probeReasoningBatch(
  server: ProbeResult,
  config: LocalModelsConfig
): Promise<ProbeResult> {
  if (server.models.length === 0 || !config.skipEmbeddingModels) {
    return server;
  }

  const timeout = config.probeTimeout ?? DEFAULT_CONFIG.probeTimeout;
  const maxConcurrent = Math.min(server.models.length, 5);
  const queue = [...server.models];
  const results: DiscoveredModel[] = [];

  // Check model IDs first for quick inference
  for (const model of server.models) {
    const inferred = inferReasoning(model.id, model.name);
    if (inferred) {
      results.push({ ...model, reasoning: true });
    }
  }

  // Probe remaining models
  const remaining = server.models.filter((m) => !inferReasoning(m.id, m.name));

  if (remaining.length === 0) {
    return { ...server, models: results, reasoningProbed: true };
  }

  // Batch probe with concurrency limit
  for (let i = 0; i < remaining.length; i += maxConcurrent) {
    const batch = remaining.slice(i, i + maxConcurrent);
    const promises = batch.map(async (model) => {
      const supported = await probeReasoningSupport(server.baseUrl, model.id, server.api, timeout);
      return { ...model, reasoning: supported };
    });
    const batchResults = await Promise.all(promises);
    results.push(...batchResults);
  }

  return { ...server, models: results, reasoningProbed: true };
}

// ---------------------------------------------------------------------------
// Main discovery function
// ---------------------------------------------------------------------------

export async function discoverServers(
  config: LocalModelsConfig
): Promise<DiscoveredServer[]> {
  const results: DiscoveredServer[] = [];

  // Determine which built-in servers to probe
  const toProbe = BUILTIN_SERVERS.filter((s) => {
    if (config.enabledServers.length === 0) return true;
    return config.enabledServers.includes(s.name);
  });

  // Add custom servers
  const customProbes: Array<{
    name: string;
    baseUrl: string;
    api: "openai-completions" | "anthropic-messages";
    endpoint: string;
  }> = (config.customServers ?? []).map((cs) => ({
    name: cs.name,
    baseUrl: cs.baseUrl,
    api: cs.api ?? "openai-completions",
    endpoint: cs.api === "openai-completions" ? "/v1/models" : "/api/tags",
  }));

  const allProbes = [...toProbe, ...customProbes];

  // Probe all servers in parallel (each has its own timeout)
  const probePromises = allProbes.map(async (probe) => {
    if (probe.endpoint === "/api/tags") {
      return probeOllama(probe.name, probe.baseUrl, config);
    }
    return probeOpenAICompatible(probe.name, probe.baseUrl, probe.endpoint, config);
  });

  const rawResults = (await Promise.all(probePromises)).filter(
    (r): r is ProbeResult => r !== null
  );

  // Probe reasoning support for each server
  const reasoningResults = await Promise.all(
    rawResults.map((r) => probeReasoningBatch(r, config))
  );

  // Convert to DiscoveredServer
  for (const r of reasoningResults) {
    results.push({
      name: r.name,
      providerName: `local-${r.name.toLowerCase().replace(/[^a-z0-9]/g, "-")}`,
      baseUrl: r.baseUrl,
      api: r.api,
      models: r.models,
    });
  }

  return results;
}
