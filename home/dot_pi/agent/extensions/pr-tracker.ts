/**
 * pr-tracker extension
 *
 * Pi adapter for the shared session PR box (~/.config/pr-box/pr_box.py), the
 * same Rex floating box Claude Code shows. This file only reports the session
 * and the PRs it opens; the tracking, status polling and drawing live in the
 * shared Python so both agents behave identically.
 *
 * On session start and on /tree, the active branch is replayed: PRs opened by
 * earlier tool calls are found (including sessions that predate this
 * extension), and add/remove entries from /pr-box apply in order. The list
 * follows /tree branches.
 *
 * When a tracked PR's CI fails, or it is approved or has changes requested, the
 * box queues a notification and this extension hands it to the agent.
 *
 * /pr-box             reopen the box in this pane, for this session
 * /pr-box add <url>   track an existing PR
 * /pr-box rm <url|#n> stop tracking a PR
 */

import { execFile, spawn } from "node:child_process";
import { existsSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";
import type { ExtensionAPI, ExtensionContext } from "@earendil-works/pi-coding-agent";

const ENTRY = "pr-tracker";
const BOX = join(homedir(), ".config/pr-box/pr_box.py");
const SESSION = `pi-${process.pid}`;
// Mirrors pr_tracking.inbox_path: PR notifications the box queued for this session.
const INBOX = join(process.env.XDG_CACHE_HOME || join(homedir(), ".cache"), "pr-box", "inbox", `${SESSION}.jsonl`);
const INBOX_TICK = 3000;
const PR_URL = /https?:\/\/[\w.-]+\/[\w.-]+\/[\w.-]+\/pull\/\d+/g;
// Mirrors pr_tracking.PR_COMMAND and PUSH_COMMAND.
const PR_COMMAND = /\bgh\s+pr\s+(create|ready|edit|merge)\b/;
const PUSH_COMMAND = /\bgit\b[^;&|]*\bpush\b/;

function box(args: string[], input?: unknown) {
  const child = spawn("python3", [BOX, ...args], {
    stdio: [input === undefined ? "ignore" : "pipe", "ignore", "ignore"],
  });
  child.on("error", () => {});
  if (input !== undefined) child.stdin?.end(JSON.stringify(input));
  child.unref();
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

/** PR URLs printed by one tool call, or none if the call does not open or touch a PR. */
function prUrls(toolName: string, input: unknown, text: string, isError: boolean): string[] {
  if (toolName === "bash") {
    const command = String((input as { command?: string } | undefined)?.command ?? "");
    return PR_COMMAND.test(command) ? extractUrls(text) : [];
  }
  if (/create_?pull_?request/i.test(toolName) && !isError) return extractUrls(text);
  return [];
}

export default function (pi: ExtensionAPI) {
  if (!process.env.REX_SESSION) return;

  let urls: string[] = [];

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
  // pi started in the same pane takes the box over, so /pr-box claims it back.
  function attach() {
    box(["set", SESSION, ...urls]);
    box(["attach", SESSION, process.cwd(), String(process.pid)]);
  }

  function start(c: ExtensionContext) {
    reconstruct(c);
    attach();
  }

  pi.on("session_start", async (_e, c) => start(c));
  pi.on("session_tree", async (_e, c) => start(c));

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
  pi.on("session_shutdown", async () => clearInterval(inbox));

  pi.on("tool_result", async (event, c) => {
    const text = resultText(event.content);
    const found = prUrls(event.toolName, event.input, text, event.isError);
    for (const url of found) {
      if (!urls.includes(url)) {
        urls.push(url);
        pi.appendEntry(ENTRY, { action: "add", url });
      }
    }
    const command = event.toolName === "bash" ? String((event.input as { command?: string })?.command ?? "") : "";
    if (command && (PR_COMMAND.test(command) || PUSH_COMMAND.test(command))) {
      box(["record", SESSION, process.cwd()], { command, output: text });
    } else if (found.length) {
      for (const url of found) box(["add", SESSION, url]);
    }
  });

  pi.registerCommand("pr-box", {
    description: "Session PR box: reopen it, or add <url> | rm <url|#n>",
    handler: async (args, c) => {
      const [sub, arg] = args.trim().split(/\s+/);
      if (!sub) return attach();
      if (sub === "add") {
        if (!arg || !extractUrls(arg).length || urls.includes(arg)) {
          return c.ui.notify("Usage: /pr-box add <PR url> (not already tracked)", "error");
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
      c.ui.notify("Usage: /pr-box [add <url> | rm <url|#n>]", "error");
    },
  });
}
