// DigitalOcean inference providers. The key is read once from a 1Password
// Environment at startup and held in memory only, so child processes
// (bash tool, MCP servers) never see it.
import { execFile } from "node:child_process";
import { promisify } from "node:util";
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

const ENVIRONMENT_ID = "mwg7j3fv3sz4hl7unqawpqskoa";
const zeroCost = { input: 0, output: 0, cacheRead: 0, cacheWrite: 0 };

const chat = (id: string, name: string, extra: object = {}) => ({
  type: "chat" as const,
  id,
  name,
  reasoning: false,
  input: ["text"] as ("text" | "image")[],
  cost: zeroCost,
  contextWindow: 128000,
  maxTokens: 16384,
  ...extra,
});

const claude = (id: string, name: string) =>
  chat(id, name, { reasoning: true, input: ["text", "image"], contextWindow: 200000, maxTokens: 64000 });

export default async function (pi: ExtensionAPI) {
  let key: string;
  try {
    const { stdout } = await promisify(execFile)(
      "op",
      // --no-masking: op conceals secrets on the child's stdout by default, which here
      // means printenv prints the literal "<concealed by 1Password>" instead of the key.
      ["run", "--no-masking", "--environment", ENVIRONMENT_ID, "--", "printenv", "MODEL_ACCESS_KEY"],
      { env: { ...process.env, OP_APP_AUTH: "1" }, timeout: 120_000 },
    );
    key = stdout.trim();
  } catch (error) {
    console.error(`digitalocean: could not read MODEL_ACCESS_KEY from 1Password: ${error}`);
    return;
  }
  if (!key) return;

  pi.registerProvider("digitalocean", {
    name: "DigitalOcean",
    baseUrl: "https://inference.do-ai.run/v1",
    api: "openai-completions",
    apiKey: key,
    compat: { supportsDeveloperRole: false },
    models: [
      chat("openai-gpt-6.2-sol", "GPT-6.2 Sol (DO)"),
      chat("kimi-k3.1-pro", "Kimi K3.1 Pro (DO)"),
      chat("glm-5.3", "GLM 5.3 (DO)"),
      chat("deepseek-v4.1-flash", "DeepSeek V4.1 Flash (DO)"),
    ],
  });

  // Claude uses the Anthropic Messages API: the OpenAI path sends `store`,
  // which DO's proxy rejects, and Messages gives thinking + prompt caching.
  pi.registerProvider("digitalocean-claude", {
    name: "DigitalOcean (Claude)",
    baseUrl: "https://inference.do-ai.run",
    api: "anthropic-messages",
    apiKey: key,
    models: [
      claude("anthropic-claude-opus-5.5", "Claude Opus 5.5 (DO)"),
      claude("anthropic-claude-sonnet-5.5", "Claude Sonnet 5.5 (DO)"),
      claude("anthropic-claude-5.5-haiku", "Claude Haiku 5.5 (DO)"),
    ],
  });
}
