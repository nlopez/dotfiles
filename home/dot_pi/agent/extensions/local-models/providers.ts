/**
 * Provider config builders.
 *
 * Converts DiscoveredServer results into Pi ProviderConfig objects.
 */

import type { ProviderConfig, ProviderModelConfig } from "@earendil-works/pi-coding-agent";
import type { DiscoveredServer } from "./config";

// ---------------------------------------------------------------------------
// Build provider config from discovered server
// ---------------------------------------------------------------------------

export function buildProviderConfig(server: DiscoveredServer): ProviderConfig {
  const providerName = server.providerName;

  // Determine thinking format based on server name
  const thinkingFormat = getThinkingFormat(server.name);

  // Build compat for the provider level
  const compat = server.name === "Ollama"
    ? {
        supportsDeveloperRole: false,
        supportsReasoningEffort: false,
      }
    : undefined;

  const base: ProviderConfig = {
    name: `${server.name} (Auto-Discovered)`,
    baseUrl: server.baseUrl,
    apiKey: providerName, // provider name as placeholder key
    api: server.api,
  };

  if (compat) {
    base.compat = compat;
  }

  // Add models
  base.models = server.models.map((m) => buildModelConfig(m, thinkingFormat));

  return base;
}

/**
 * Map a model to a Pi ProviderModelConfig.
 */
function buildModelConfig(
  model: DiscoveredServer["models"][number],
  defaultThinkingFormat: string | undefined
): ProviderModelConfig {
  const modelCompat: Record<string, unknown> = {};

  // Apply thinking format if the model supports reasoning
  if (model.reasoning && defaultThinkingFormat) {
    modelCompat.thinkingFormat = defaultThinkingFormat;
  }

  // For reasoning models, set up thinking level map
  const thinkingLevelMap = model.reasoning
    ? {
        off: null, // reasoning models typically can't disable thinking
        minimal: "low",
        low: "low",
        medium: "medium",
        high: "high",
        xhigh: "max",
      }
    : undefined;

  const config: ProviderModelConfig = {
    id: model.id,
    name: model.name ?? model.id,
    reasoning: model.reasoning,
    input: model.input,
    cost: model.cost,
    contextWindow: model.contextWindow,
    maxTokens: model.maxTokens,
  };

  if (thinkingLevelMap) {
    config.thinkingLevelMap = thinkingLevelMap;
  }

  if (Object.keys(modelCompat).length > 0) {
    config.compat = modelCompat;
  }

  return config;
}

/**
 * Determine the thinking format for a server type.
 */
function getThinkingFormat(serverName: string): string | undefined {
  switch (serverName) {
    case "Ollama":
      return "qwen"; // Ollama uses enable_thinking
    case "LM Studio":
      return "qwen-chat-template"; // LM Studio may use chat_template_kwargs
    case "vLLM":
      return "qwen";
    case "SGLang":
      return "qwen";
    case "TGI":
      return "qwen";
    case "KoboldCpp":
      return "qwen-chat-template";
    case "llamafile":
      return "qwen-chat-template";
    default:
      return undefined;
  }
}
