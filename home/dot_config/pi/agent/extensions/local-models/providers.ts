/**
 * Builds Pi ProviderConfig from a DiscoveredServer.
 */

import type { ProviderConfig, ProviderModelConfig } from "@earendil-works/pi-coding-agent";
import type { DiscoveredServer } from "./config";

export function buildProviderConfig(server: DiscoveredServer): ProviderConfig {
  const config: ProviderConfig = {
    name: `${server.name} (Local)`,
    baseUrl: server.baseUrl,
    apiKey: server.apiKey,
    api: server.api,
    models: server.models.map((m) => buildModelConfig(m, server.thinkingFormat)),
  };

  if (server.authHeader) {
    config.authHeader = true;
  }

  return config;
}

function buildModelConfig(
  model: DiscoveredServer["models"][number],
  serverThinkingFormat: string | undefined,
): ProviderModelConfig {
  const config: ProviderModelConfig = {
    id: model.id,
    name: model.name ?? model.id,
    reasoning: model.reasoning,
    input: model.input,
    cost: model.cost,
    contextWindow: model.contextWindow,
    maxTokens: model.maxTokens,
  };

  if (model.reasoning && serverThinkingFormat) {
    config.compat = { ...model.compat, thinkingFormat: serverThinkingFormat };
  } else if (model.compat) {
    config.compat = model.compat;
  }

  return config;
}
