/**
 * Discovery: probe omlx / lm-studio for reachability and model lists.
 */

import type { DiscoveredServer, LocalModelsConfig } from "./config";
import { KNOWN_SERVERS, DEFAULT_CONFIG, isLikelyChatModel, inferReasoning } from "./config";

interface OpenAIModelsResponse {
  object: string;
  data: Array<{ id: string; name?: string }>;
}

async function probeServer(
  server: (typeof KNOWN_SERVERS)[number],
  config: LocalModelsConfig,
): Promise<DiscoveredServer | null> {
  const url = `${server.baseUrl}${server.modelsEndpoint}`;
  const timeout = config.probeTimeout ?? DEFAULT_CONFIG.probeTimeout;

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeout);

  try {
    const headers: Record<string, string> = { Accept: "application/json" };
    if (server.authHeader && server.apiKey) {
      headers["Authorization"] = `Bearer ${server.apiKey}`;
    }

    const response = await fetch(url, { signal: controller.signal, headers });
    if (!response.ok) return null;

    const data = (await response.json()) as OpenAIModelsResponse;
    if (!data.data) return null;

    const models = data.data
      .filter((m) => isLikelyChatModel(m.id))
      .map((m) => ({
        id: m.id,
        name: m.name,
        reasoning: inferReasoning(m.id, m.name),
        input: ["text"] as const,
        contextWindow: config.defaultContextWindow ?? DEFAULT_CONFIG.defaultContextWindow,
        maxTokens: config.defaultMaxTokens ?? DEFAULT_CONFIG.defaultMaxTokens,
        cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0 },
      }));

    return {
      name: server.name,
      providerName: `local-${server.name}`,
      baseUrl: server.baseUrl,
      api: server.api,
      models,
      thinkingFormat: server.thinkingFormat,
      apiKey: server.apiKey,
      authHeader: server.authHeader,
    };
  } catch {
    return null;
  } finally {
    clearTimeout(timer);
  }
}

export async function discoverServers(config: LocalModelsConfig): Promise<DiscoveredServer[]> {
  const enabled = KNOWN_SERVERS.filter((s) => {
    if (!config.enabledServers || config.enabledServers.length === 0) return true;
    return config.enabledServers.includes(s.name);
  });

  const results = await Promise.all(enabled.map((s) => probeServer(s, config)));
  return results.filter((r): r is DiscoveredServer => r !== null);
}
