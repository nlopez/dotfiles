/**
 * rex-tab-title extension
 *
 * Updates Pi's terminal title to `<task>` inside Rex so Rex tabs show the
 * current task instead of `π - <cwd>`, and renames the Rex session and tab to
 * the same task the way Claude Code's session-start hook names them.
 *
 * Sets an immediate cleaned snippet from the first user prompt, refines it in
 * the background with a short 2-5 word summary via `pi.setSessionName()`, and
 * always defers to explicit `/name` changes. Rex labels are only replaced
 * while they still hold the directory name or a `Window <id>` default.
 */

import { basename } from "node:path";
import { complete, completeSimple } from "@earendil-works/pi-ai/compat";
import type { ExtensionAPI, ExtensionContext } from "@earendil-works/pi-coding-agent";

type Model = Parameters<typeof completeSimple>[0];

const MAX_TITLE_CHARS = 48;
const MAX_FALLBACK_CHARS = 40;
const TITLE_TIMEOUT_MS = 10_000;
const NEEDS_EXPLICIT_REASONING_OFF = new Set(["openai-codex-responses"]);

export function formatTabTitle(label: string): string {
  const clean = label
    .replace(/[\x00-\x1f\x7f]+/g, " ")
    .replace(/\s+/g, " ")
    .trim();
  if (!clean) return "";
  return clean.length > MAX_TITLE_CHARS ? `${clean.slice(0, MAX_TITLE_CHARS - 1).trimEnd()}…` : clean;
}

export function fallbackTitleFromPrompt(prompt: string): string {
  let text = prompt
    .replace(/[\x00-\x1f\x7f]+/g, " ")
    .replace(/[`*_#]+/g, "")
    .replace(/\s+/g, " ")
    .trim();
  const slashMatch = text.match(/^\/\S+\s+(.+)$/);
  if (slashMatch) text = slashMatch[1].trim();
  if (text.length <= MAX_FALLBACK_CHARS) return text;
  const cut = text.slice(0, MAX_FALLBACK_CHARS);
  const lastSpace = cut.lastIndexOf(" ");
  return (lastSpace > 12 ? cut.slice(0, lastSpace) : cut).trimEnd() + "…";
}

export function cleanGeneratedTitle(raw: string): string {
  const firstLine =
    raw
      .split(/\r?\n/)
      .map((line) => line.trim())
      .find(Boolean) ?? "";
  return firstLine
    .replace(/^✳\s*/, "")
    .replace(/^["'“”‘’]+|["'“”‘’]+$/g, "")
    .replace(/[.!?:;]+$/, "")
    .replace(/\s+/g, " ")
    .trim()
    .slice(0, MAX_TITLE_CHARS);
}

export function rexLabelFromTitle(title: string): string {
  return title
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, " ")
    .trim()
    .split(" ")
    .filter(Boolean)
    .slice(0, 4)
    .join("-")
    .slice(0, MAX_TITLE_CHARS);
}

export function isDefaultLabel(label: string | undefined, cwd: string): boolean {
  if (!label) return true;
  return label === (basename(cwd) || cwd) || /^Window [0-9a-f]{6,8}$/i.test(label);
}

export function pickTitleModel(
  activeModel: Model | undefined,
  registry: Pick<ExtensionContext["modelRegistry"], "getAvailable">,
): Model | undefined {
  if (!activeModel) return undefined;
  const sameProvider = registry.getAvailable().filter((m) => m.provider === activeModel.provider);
  return (
    sameProvider.find((m) => /haiku/i.test(m.id)) ??
    sameProvider.find((m) => /flash/i.test(m.id)) ??
    sameProvider.find((m) => /(?:mini|nano|luna)/i.test(m.id)) ??
    activeModel
  );
}

function firstUserText(ctx: ExtensionContext): string | undefined {
  for (const entry of ctx.sessionManager.getBranch()) {
    if (entry.type !== "message" || entry.message.role !== "user") continue;
    const content = entry.message.content;
    if (typeof content === "string") return content;
    return content
      .filter((part): part is { type: "text"; text: string } => part.type === "text" && typeof part.text === "string")
      .map((part) => part.text)
      .join(" ");
  }
  return undefined;
}

function defaultLabel(ctx: ExtensionContext): string {
  return basename(ctx.cwd) || ctx.cwd || "pi";
}

export default function (pi: ExtensionAPI) {
  if (!process.env.REX_SESSION && process.env.TERM_PROGRAM !== "rex") return;

  let pendingTimer: ReturnType<typeof setTimeout> | undefined;
  let inflight: AbortController | undefined;
  const attemptedSessions = new Set<string>();

  function applyTitle(ctx: ExtensionContext, label: string): void {
    if (!ctx.hasUI) return;
    ctx.ui.setTitle(formatTabTitle(label));
  }

  let lastLabel: string | undefined;

  async function rexJson<T>(args: string[]): Promise<T | undefined> {
    try {
      const result = await pi.exec("rex", args, { timeout: 5_000 });
      return result.code === 0 ? (JSON.parse(result.stdout) as T) : undefined;
    } catch {
      return undefined;
    }
  }

  async function syncRexLabels(ctx: ExtensionContext, title: string): Promise<void> {
    const session = process.env.REX_SESSION;
    const label = rexLabelFromTitle(title);
    if (!session || !label || label === lastLabel) return;

    const info = await rexJson<{ label?: string; windows?: { window_id: string; label: string }[] }>([
      "session",
      "inspect",
      session,
      "--json",
    ]);
    if (!info) return;
    const previous = lastLabel;
    const block = process.env.REX_BLOCK;
    const blockInfo = block
      ? await rexJson<{ block?: { window_id?: string } }>(["block", "inspect", block, "--json"])
      : undefined;
    const window = info.windows?.find((entry) => entry.window_id === blockInfo?.block?.window_id);

    // Session and tab are renamed apart: a name someone chose for the session
    // leaves the tab free to follow the task.
    const sessionOurs = info.label === previous || isDefaultLabel(info.label, ctx.cwd);
    const windowOurs =
      !!window && window.label !== label && (window.label === previous || isDefaultLabel(window.label, ctx.cwd));
    if (!sessionOurs && !windowOurs) return;
    lastLabel = label;

    if (sessionOurs && info.label !== label) await rexJson(["session", "rename", session, label]);
    if (window && windowOurs) await rexJson(["window", "rename", "-s", session, window.window_id, label]);
  }

  function cancelPending(): void {
    if (pendingTimer) {
      clearTimeout(pendingTimer);
      pendingTimer = undefined;
    }
    if (inflight) {
      inflight.abort();
      inflight = undefined;
    }
  }

  async function summarizeAndName(sessionId: string, prompt: string, ctx: ExtensionContext): Promise<void> {
    const model = pickTitleModel(ctx.model, ctx.modelRegistry);
    if (!model) return;

    const auth = await ctx.modelRegistry.getApiKeyAndHeaders(model);
    if (!auth?.ok) return;

    const requestModel = auth.baseUrl ? { ...model, baseUrl: auth.baseUrl } : model;
    const controller = new AbortController();
    inflight = controller;
    const timeout = setTimeout(() => controller.abort(), TITLE_TIMEOUT_MS);

    try {
      const context = {
        systemPrompt: "",
        messages: [
          {
            role: "user" as const,
            content: [
              {
                type: "text" as const,
                text:
                  "Summarize this user request as a 2 to 5 word title in sentence case. " +
                  "Output only the title, no quotes or punctuation.\n\n" +
                  prompt.slice(0, 1000),
              },
            ],
            timestamp: Date.now(),
          },
        ],
      };
      const options = {
        apiKey: auth.apiKey,
        headers: auth.headers,
        env: auth.env,
        signal: controller.signal,
        cacheRetention: "none" as const,
        maxTokens: 24,
      };
      const response = NEEDS_EXPLICIT_REASONING_OFF.has(requestModel.api)
        ? await complete(requestModel, context, { ...options, reasoningEffort: "none" })
        : await completeSimple(requestModel, context, options);

      if (controller.signal.aborted || response.stopReason !== "stop") return;
      if (ctx.sessionManager.getSessionId() !== sessionId || pi.getSessionName()) return;

      const raw = response.content
        .filter((part): part is { type: "text"; text: string } => part.type === "text")
        .map((part) => part.text)
        .join(" ");
      const title = cleanGeneratedTitle(raw);
      if (!title) return;
      pi.setSessionName(title);
      await syncRexLabels(ctx, title);
    } catch {
      // Fallback title is already shown; ignore background title errors.
    } finally {
      clearTimeout(timeout);
      if (inflight === controller) inflight = undefined;
    }
  }

  pi.on("session_start", async (_event, ctx) => {
    cancelPending();
    // Schedule after InteractiveMode.rebindCurrentSession finishes updateTerminalTitle().
    pendingTimer = setTimeout(() => {
      pendingTimer = undefined;
      const name = pi.getSessionName();
      if (name) {
        applyTitle(ctx, name);
        void syncRexLabels(ctx, name);
        return;
      }
      const prompt = firstUserText(ctx);
      const title = prompt ? fallbackTitleFromPrompt(prompt) : "";
      applyTitle(ctx, title || defaultLabel(ctx));
      if (title) void syncRexLabels(ctx, title);
    }, 0);
  });

  pi.on("session_info_changed", async (event, ctx) => {
    if (pendingTimer) {
      clearTimeout(pendingTimer);
      pendingTimer = undefined;
    }
    const name = event.name?.trim();
    applyTitle(ctx, name || defaultLabel(ctx));
    if (name) void syncRexLabels(ctx, name);
  });

  pi.on("before_agent_start", async (event, ctx) => {
    if (event.messageType !== "user" || pi.getSessionName()) return;
    const sessionId = ctx.sessionManager.getSessionId();
    if (attemptedSessions.has(sessionId)) return;
    attemptedSessions.add(sessionId);

    const fallback = fallbackTitleFromPrompt(event.prompt);
    if (fallback) {
      applyTitle(ctx, fallback);
      void syncRexLabels(ctx, fallback);
    }
    void summarizeAndName(sessionId, event.prompt, ctx);
  });

  pi.on("session_shutdown", async () => {
    cancelPending();
  });
}
