/**
 * pr-tracker extension
 *
 * Pi adapter for the shared session PR box (~/.config/argus-pr/argus_pr.py), the
 * same Rex tiled pane Claude Code shows. This file only reports the session
 * and the PRs it opens; the tracking, status polling and drawing live in the
 * shared Python so both agents behave identically.
 *
 * On session start and on /tree, the active branch is replayed: PRs opened by
 * earlier tool calls are found (including sessions that predate this
 * extension), and add/remove entries from /argus-pr apply in order. The list
 * follows /tree branches.
 *
 * When a tracked PR's CI fails, or it is approved or has changes requested, the
 * box queues a notification and this extension hands it to the agent.
 *
 * /argus-pr             reopen the box in this pane, for this session
 * /argus-pr add <url>   track an existing PR
 * /argus-pr rm <url|#n> stop tracking a PR
 */

import { execFile, spawn } from "node:child_process";
import { existsSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";
import type { ExtensionAPI, ExtensionContext } from "@earendil-works/pi-coding-agent";
import { Type } from "typebox";

const ENTRY = "pr-tracker";
const BOX = join(homedir(), ".config/argus-pr/argus_pr.py");
const SESSION = `pi-${process.pid}`;
const CACHE_DIR = join(process.env.XDG_CACHE_HOME || join(homedir(), ".cache"), "argus-pr");
// Mirrors pr_tracking._session_path: tracked PR list and queued notifications for this session.
const SESSION_FILE = join(CACHE_DIR, "sessions", `${SESSION}.json`);
const INBOX = join(CACHE_DIR, "inbox", `${SESSION}.jsonl`);
const INBOX_TICK = 3000;
const PR_URL = /https?:\/\/[\w.-]+\/[\w.-]+\/[\w.-]+\/pull\/\d+/g;
// Mirrors pr_tracking.PR_COMMAND and PUSH_COMMAND.
const PR_COMMAND = /\bgh\s+pr\s+(create|ready|edit|merge)\b/;
const PUSH_COMMAND = /\bgit\b[^;&|]*\bpush\b/;
// Strip ticking poll timers and in-flight pending counts so context deltas only fire on real state changes.
const VOLATILE_STATUS = /  (?:next \S+|checking)(?=  error:|$)/gm;
const PENDING_COUNT = /\bchecks pending \d+\/\d+/g;

function normalizeStatus(raw: string): string {
  return raw.replace(VOLATILE_STATUS, "").replace(PENDING_COUNT, "checks pending").trim();
}

function box(args: string[], input?: unknown) {
  const child = spawn("python3", [BOX, ...args], {
    stdio: [input === undefined ? "ignore" : "pipe", "ignore", "ignore"],
  });
  child.on("error", () => {});
  if (input !== undefined) child.stdin?.end(JSON.stringify(input));
  child.unref();
}

function runBox(args: string[]): Promise<string> {
  return new Promise((resolve) => {
    execFile("python3", [BOX, ...args], { timeout: 5000 }, (err, stdout) => {
      resolve(err ? "" : String(stdout ?? "").trim());
    });
  });
}

function extractUrls(text: string): string[] {
  return [...text.matchAll(PR_URL)].map((m) => m[0]);
}

function resultText(content: unknown): string {
  if (!Array.isArray(content)) return "";
  return content
    .map((c) => (c && typeof c === "object" && "text" in c ? String((c as { text: unknown }).text) : ""))
    .join("\n");
}

/** Shell command string for bash or context-mode shell tools, or "" otherwise. */
function shellCommand(toolName: string, input: unknown): string {
  const args = (input ?? {}) as { command?: string; code?: string; language?: string; commands?: unknown };
  if (toolName === "bash") return String(args.command ?? "");
  if (toolName === "ctx_execute" && (!args.language || args.language === "shell")) return String(args.code ?? "");
  if (toolName === "ctx_batch" && Array.isArray(args.commands)) return args.commands.map(String).join("\n");
  return "";
}

/** PR URLs printed by one tool call, or none if the call does not open or touch a PR. */
function prUrls(toolName: string, input: unknown, text: string, isError: boolean): string[] {
  const command = shellCommand(toolName, input);
  if (command) return PR_COMMAND.test(command) ? extractUrls(text) : [];
  if (/create_?pull_?request/i.test(toolName) && !isError) return extractUrls(text);
  return [];
}

export default function (pi: ExtensionAPI) {
  if (!process.env.REX_SESSION) return;

  let urls: string[] = [];
  let lastSnapshot = "";

  // Replays the active branch in order, so a later remove wins over an earlier detection.
  function reconstruct(c: ExtensionContext) {
    const found = new Set<string>();
    const inputs = new Map<string, unknown>();
    for (const entry of c.sessionManager.getBranch()) {
      if (entry.type === "message") {
        const msg = entry.message as any;
        if (msg.role === "assistant" && Array.isArray(msg.content)) {
          for (const part of msg.content) if (part?.type === "toolCall") inputs.set(part.id, part.arguments);
        } else if (msg.role === "toolResult") {
          prUrls(msg.toolName, inputs.get(msg.toolCallId), resultText(msg.content), msg.isError).forEach((u) =>
            found.add(u),
          );
        }
        continue;
      }
      if (entry.type !== "custom" || entry.customType !== ENTRY) continue;
      const data = entry.data as { action: "add" | "remove"; url: string };
      if (data.action === "add") found.add(data.url);
      else found.delete(data.url);
    }
    urls = [...found];
  }

  // Points the pane's box at this session, opening it if it isn't showing. Another
  // pi started in the same pane takes the box over, so /argus-pr claims it back.
  function attach() {
    box(["set", SESSION, ...urls]);
    box(["attach", SESSION, process.cwd(), String(process.pid)]);
  }

  function start(c: ExtensionContext, reason?: string) {
    lastSnapshot = "";
    reconstruct(c);
    if (reason === "new" || (reason === "startup" && !urls.length)) {
      urls = [];
      box(["reset", SESSION]);
      box(["attach", SESSION, process.cwd(), String(process.pid)]);
      return;
    }
    attach();
  }

  pi.on("session_start", async (e, c) => start(c, (e as { reason?: string } | undefined)?.reason));
  pi.on("session_tree", async (_e, c) => start(c));
  pi.on("session_compact", () => {
    lastSnapshot = "";
  });

  // Append a hidden delta message only when tracked PR state meaningfully changes, keeping
  // the system prompt static (no prompt-cache bust) and re-emitting once after compaction.
  pi.on("before_agent_start", async (event) => {
    if (!urls.length && !existsSync(SESSION_FILE)) {
      lastSnapshot = "";
      return;
    }
    const stable = normalizeStatus(await runBox(["status", SESSION]));
    if (!stable || stable === "no PRs tracked") {
      lastSnapshot = "";
      return;
    }
    if (stable === lastSnapshot) return;
    lastSnapshot = stable;
    if (event.messageType === "custom") return;
    return {
      message: {
        customType: "pr-status",
        content: `<tracked_prs>\n${stable}\n</tracked_prs>`,
        display: false,
      },
    };
  });

  pi.registerTool({
    name: "pr_status",
    label: "PR Status",
    description:
      "Read cached status of PRs tracked in this session (state, head SHA, CI checks, failing checks, review, next poll), or start tracking a PR URL.",
    promptSnippet: "Check cached CI/review status of tracked PRs or add a PR URL to track",
    promptGuidelines: [
      "Use pr_status instead of shelling out to argus_pr.py when you need the latest cached status or poll timer for tracked PRs.",
    ],
    parameters: Type.Object({
      add: Type.Optional(Type.String({ description: "Optional PR URL to start tracking before reading status" })),
    }),
    async execute(_toolCallId, params) {
      if (params.add) {
        const [url] = extractUrls(params.add);
        if (!url) {
          return {
            content: [{ type: "text", text: `Invalid PR URL: ${params.add}` }],
            details: { session: SESSION, error: "invalid_url" },
            isError: true,
          };
        }
        if (!urls.includes(url)) {
          urls.push(url);
          pi.appendEntry(ENTRY, { action: "add", url });
        }
        await runBox(["add", SESSION, url]);
      }
      const text = (await runBox(["status", SESSION])) || "no PRs tracked";
      return {
        content: [{ type: "text", text }],
        details: { session: SESSION, count: urls.length },
      };
    },
  });

  // Deliver the box's notifications (CI failed, approved, changes requested): start a turn when
  // idle, or queue a follow-up when the agent is working.
  let draining = false;
  const inbox = setInterval(() => {
    if (draining || !existsSync(INBOX)) return;
    draining = true;
    execFile("python3", [BOX, "drain", SESSION], (err, stdout) => {
      draining = false;
      const text = String(stdout ?? "").trim();
      if (err || !text) return;
      pi.sendMessage(
        { customType: "pr-notify", content: text, display: true },
        { triggerTurn: true, deliverAs: "followUp" },
      );
    });
  }, INBOX_TICK);
  inbox.unref();
  pi.on("session_shutdown", async (e) => {
    clearInterval(inbox);
    if ((e as { reason?: string } | undefined)?.reason === "new") {
      urls = [];
      box(["reset", SESSION]);
    }
  });

  pi.on("tool_result", async (event, c) => {
    const text = resultText(event.content);
    const found = prUrls(event.toolName, event.input, text, event.isError);
    for (const url of found) {
      if (!urls.includes(url)) {
        urls.push(url);
        pi.appendEntry(ENTRY, { action: "add", url });
      }
    }
    const command = shellCommand(event.toolName, event.input);
    if (command && (PR_COMMAND.test(command) || PUSH_COMMAND.test(command))) {
      box(["record", SESSION, process.cwd()], { command, output: text });
    } else if (found.length) {
      for (const url of found) box(["add", SESSION, url]);
    }
  });

  pi.registerCommand("argus-pr", {
    description: "Session PR box: reopen it, or add <url> | rm <url|#n>",
    handler: async (args, c) => {
      const [sub, arg] = args.trim().split(/\s+/);
      if (!sub) return attach();
      if (sub === "add") {
        if (!arg || !extractUrls(arg).length || urls.includes(arg)) {
          return c.ui.notify("Usage: /argus-pr add <PR url> (not already tracked)", "error");
        }
        urls.push(arg);
        pi.appendEntry(ENTRY, { action: "add", url: arg });
        return box(["set", SESSION, ...urls]);
      }
      if (sub === "rm") {
        const n = arg?.replace(/^#/, "");
        const url = urls.find((u) => u === arg || u.endsWith(`/pull/${n}`));
        if (!url) return c.ui.notify(`Not tracked: ${arg ?? ""}`, "error");
        urls = urls.filter((u) => u !== url);
        pi.appendEntry(ENTRY, { action: "remove", url });
        return box(["set", SESSION, ...urls]);
      }
      c.ui.notify("Usage: /argus-pr [add <url> | rm <url|#n>]", "error");
    },
  });
}
