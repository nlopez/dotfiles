/**
 * openrouter-cost extension
 *
 * Shows this machine's OpenRouter key spend against its limit in the footer,
 * e.g. "or $0.04 today / $19.96 left", refreshed from GET /api/v1/key when a
 * session starts and when the agent goes idle (debounced).
 *
 * /or-cost prints the full breakdown: today, week, month, and the limit reset.
 *
 * Does nothing on machines with no OpenRouter key in auth.json.
 */

import { readFileSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";
import type { ExtensionAPI, ExtensionContext } from "@earendil-works/pi-coding-agent";

const STATUS_KEY = "openrouter";
const AUTH = join(process.env.PI_CODING_AGENT_DIR || join(homedir(), ".pi", "agent"), "auth.json");
const REFRESH_MS = 60_000;
const RED = "\x1b[31m";
const RESET = "\x1b[0m";

type KeyInfo = {
  limit: number | null;
  limit_remaining: number | null;
  usage_daily: number;
  usage_weekly: number;
  usage_monthly: number;
  effective_budget?: { resets_at?: string };
};

function apiKey(): string | undefined {
  if (process.env.OPENROUTER_API_KEY) return process.env.OPENROUTER_API_KEY;
  try {
    const key = JSON.parse(readFileSync(AUTH, "utf8"))?.openrouter?.key;
    return typeof key === "string" && key ? key : undefined;
  } catch {
    return undefined;
  }
}

async function fetchKey(key: string): Promise<KeyInfo> {
  const res = await fetch("https://openrouter.ai/api/v1/key", {
    headers: { Authorization: `Bearer ${key}` },
    signal: AbortSignal.timeout(10_000),
  });
  if (!res.ok) throw new Error(`OpenRouter ${res.status}`);
  return ((await res.json()) as { data: KeyInfo }).data;
}

const usd = (n: number | null | undefined) => `$${(n ?? 0).toFixed(2)}`;

export default function (pi: ExtensionAPI) {
  const key = apiKey();
  if (!key) return;

  let info: KeyInfo | null = null;
  let last = 0;
  let pending: Promise<void> | null = null;

  async function refresh(ctx: ExtensionContext, force = false) {
    if (pending) return pending;
    if (!force && Date.now() - last < REFRESH_MS) return;
    last = Date.now();
    pending = (async () => {
      try {
        info = await fetchKey(key);
        const left = info.limit_remaining;
        const low = info.limit ? (left ?? 0) / info.limit < 0.2 : (left ?? 0) < 1;
        const tail = left === null ? "" : ` / ${low ? RED : ""}${usd(left)} left${low ? RESET : ""}`;
        ctx.ui.setStatus(STATUS_KEY, `${usd(info.usage_daily)} today${tail}`);
      } catch {
        // Keep the last known figure; the next refresh retries.
      } finally {
        pending = null;
      }
    })();
    return pending;
  }

  pi.on("session_start", async (_e, ctx) => refresh(ctx, true));
  pi.on("agent_settled", async (_e, ctx) => refresh(ctx));

  pi.registerCommand("or-cost", {
    description: "Show OpenRouter spend for this machine's key",
    handler: async (_args, ctx) => {
      await refresh(ctx, true);
      if (!info) return ctx.ui.notify("OpenRouter: no key or API unreachable", "error");
      const reset = info.effective_budget?.resets_at?.slice(0, 10);
      const limit = info.limit ? `${usd(info.limit)} limit${reset ? `, resets ${reset}` : ""}` : "no limit";
      ctx.ui.notify(
        `OpenRouter: ${usd(info.usage_daily)} today, ${usd(info.usage_weekly)} this week, ` +
          `${usd(info.usage_monthly)} this month (${limit}, ${usd(info.limit_remaining)} left)`,
      );
    },
  });
}
