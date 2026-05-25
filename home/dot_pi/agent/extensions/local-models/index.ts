/**
 * Local Models Extension
 *
 * Auto-discovers local model servers (Ollama, LM Studio, vLLM, etc.)
 * by probing common endpoints and registers them as Pi providers.
 *
 * Configuration: ~/.pi/agent/settings.json → localModels key
 *
 * Usage:
 *   - Automatically probes on startup
 *   - /refresh-local-models — manually re-probe
 *   - Configurable via settings.json.localModels
 */

import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { discoverServers } from "./discover";
import { buildProviderConfig } from "./providers";
import { loadConfig } from "./config";

// Track registered provider names for cleanup on refresh
const registeredProviders = new Set<string>();

/**
 * Discover and register local model servers.
 * Returns a summary of what was found for UI feedback.
 */
async function discoverAndRegister(pi: ExtensionAPI): Promise<string[]> {
  const config = loadConfig();
  const discovered = await discoverServers(config);
  const summary: string[] = [];

  if (discovered.length === 0) {
    summary.push("No local model servers found.");
    return summary;
  }

  for (const server of discovered) {
    // Skip if provider already registered
    if (registeredProviders.has(server.providerName)) {
      summary.push(`  ${server.name}: ${server.models.length} models (already registered)`);
      continue;
    }

    const providerConfig = buildProviderConfig(server);

    // Register the provider
    pi.registerProvider(server.providerName, providerConfig);
    registeredProviders.add(server.providerName);

    summary.push(`  ${server.name} (${server.baseUrl}): ${server.models.length} models`);
  }

  return summary;
}

/**
 * Clear all auto-discovered providers.
 */
function clearDiscoveredProviders(pi: ExtensionAPI): void {
  for (const name of registeredProviders) {
    try {
      pi.unregisterProvider(name);
    } catch {
      // Ignore errors from unregistering unknown providers
    }
  }
  registeredProviders.clear();
}

// ---------------------------------------------------------------------------
// Extension factory
// ---------------------------------------------------------------------------

export default async function localModelsExtension(pi: ExtensionAPI) {
  const config = loadConfig();

  // Phase 1: Discover and register on startup
  const summary = await discoverAndRegister(pi);

  if (config.autoEnable) {
    pi.on("session_start", async (_event, ctx) => {
      if (_event.reason === "startup") {
        ctx.ui.notify(
          `Local models: ${summary.join(", ")}`,
          "info"
        );
      }
    });
  }

  // Phase 2: Register /refresh-local-models command
  pi.registerCommand("refresh-local-models", {
    description: "Re-discover local model servers and update registered providers",
    handler: async (_args, ctx) => {
      // Clear old providers
      clearDiscoveredProviders(pi);

      // Re-discover
      const newSummary = await discoverAndRegister(pi);

      if (newSummary.length === 0) {
        ctx.ui.notify("No local model servers found.", "warning");
      } else {
        ctx.ui.notify(
          `Local models refreshed:\n${newSummary.join("\n")}`,
          "info"
        );
      }
    },
  });

  // Phase 3: On session reload, re-discover to catch new servers
  pi.on("session_start", async (event, ctx) => {
    if (event.reason === "reload" && config.autoEnable) {
      clearDiscoveredProviders(pi);
      const newSummary = await discoverAndRegister(pi);
      if (newSummary.length > 0) {
        ctx.ui.notify(
          `Local models refreshed:\n${newSummary.join("\n")}`,
          "info"
        );
      }
    }
  });
}
