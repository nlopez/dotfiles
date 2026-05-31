/**
 * Provider config builders.
 *
 * Converts DiscoveredServer results into Pi ProviderConfig objects.
 */

import type { ProviderConfig, ProviderModelConfig } from "@earendil-works/pi-coding-agent";
import type { DiscoveredServer } from "./config";

/**
 * Build a Pi ProviderConfig from a discovered server.
 */
export function buildProviderConfig(server: DiscoveredServer): ProviderConfig {
  const providerName = server.providerName;

  const base: ProviderConfig = {
    name: `${server.name} (Auto-Discovered)`,
    baseUrl: server.baseUrl,
    apiKey: providerName,
    api: server.api,
  };

  // Add models with per-model thinking format
  base.models = server.models.map((m) => buildModelConfig(m, server.thinkingFormat));

  return base;
}

/**
 * Build a Pi ModelConfig from a discovered model, applying the server's
 * default thinking format when the model supports reasoning.
 */
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

  // Set up thinking support for reasoning models
  if (model.reasoning) {
    config.thinkingLevelMap = {
      off: null,
      minimal: "low",
      low: "low",
      medium: "medium",
      high: "high",
      xhigh: "max",
    };

    // Apply the server's default thinking format if supported
    if (serverThinkingFormat) {
      config.compat = {
        ...model.compat,
        thinkingFormat: serverThinkingFormat,
      };
    } else {
      config.compat = model.compat;
    }
  } else {
    config.compat = model.compat;
  }

  return config;
}
