/**
 * Local Models Extension
 *
 * Auto-discovers local model servers by probing known endpoints
 * and registers them as Pi providers using their documented APIs.
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

const registeredProviders = new Set<string>();

async function discoverAndRegister(pi: ExtensionAPI): Promise<string[]> {
  const config = loadConfig();
  const discovered = await discoverServers(config);
  const summary: string[] = [];

  if (discovered.length === 0) {
    summary.push("No local model servers found.");
    return summary;
  }

  for (const server of discovered) {
    if (registeredProviders.has(server.providerName)) {
      summary.push(`  ${server.name}: ${server.models.length} models (already registered)`);
      continue;
    }

    pi.registerProvider(server.providerName, buildProviderConfig(server));
    registeredProviders.add(server.providerName);
    summary.push(`  ${server.name} (${server.baseUrl}): ${server.models.length} models`);
  }

  return summary;
}

function clearDiscoveredProviders(pi: ExtensionAPI): void {
  for (const name of registeredProviders) {
    try {
      pi.unregisterProvider(name);
    } catch {
      /* ignore */
    }
  }
  registeredProviders.clear();
}

export default async function localModelsExtension(pi: ExtensionAPI) {
  const config = loadConfig();

  // Discover on startup
  const summary = await discoverAndRegister(pi);

  if (config.autoEnable) {
    pi.on("session_start", async (event, ctx) => {
      if (event.reason === "startup") {
        ctx.ui.notify(`Local models: ${summary.join(", ")}`, "info");
      }
    });
  }

  // Manual refresh command
  pi.registerCommand("refresh-local-models", {
    description: "Re-discover local model servers and update registered providers",
    handler: async (_args, ctx) => {
      clearDiscoveredProviders(pi);
      const newSummary = await discoverAndRegister(pi);
      if (newSummary.length === 0) {
        ctx.ui.notify("No local model servers found.", "warning");
      } else {
        ctx.ui.notify(`Local models refreshed:\n${newSummary.join("\n")}`, "info");
      }
    },
  });

  // Re-discover on reload
  pi.on("session_start", async (event, ctx) => {
    if (event.reason === "reload" && config.autoEnable) {
      clearDiscoveredProviders(pi);
      const newSummary = await discoverAndRegister(pi);
      if (newSummary.length > 0) {
        ctx.ui.notify(`Local models refreshed:\n${newSummary.join("\n")}`, "info");
      }
    }
  });
}
