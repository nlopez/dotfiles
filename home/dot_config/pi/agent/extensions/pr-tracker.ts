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
 * extension), and add/remove entries from /prs apply in order. The list follows
 * /tree branches.
 *
 * /prs                 reopen the box if it was closed
 * /prs add <url>       track an existing PR
 * /prs rm <url|#n>     stop tracking a PR
 */

import { spawn } from "node:child_process";
import { homedir } from "node:os";
import { join } from "node:path";
import type { ExtensionAPI, ExtensionContext } from "@earendil-works/pi-coding-agent";

const ENTRY = "pr-tracker";
const BOX = join(homedir(), ".config/pr-box/pr_box.py");
const SESSION = `pi-${process.pid}`;
const PR_URL = /https?:\/\/[\w.-]+\/[\w.-]+\/[\w.-]+\/pull\/\d+/g;
// Mirrors pr_tracking.PR_COMMAND and PUSH_COMMAND.
const PR_COMMAND = /\bgh\s+pr\s+(create|ready|edit|merge)\b/;
const PUSH_COMMAND = /\bgit\b[^;&|]*\bpush\b/;

function box(args: string[], input?: unknown) {
  const child = spawn("python3", [BOX, ...args], { stdio: [input === undefined ? "ignore" : "pipe", "ignore", "ignore"] });
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

  function start(c: ExtensionContext) {
    reconstruct(c);
    box(["set", SESSION, ...urls]);
    box(["attach", SESSION, process.cwd(), String(process.pid)]);
  }

  pi.on("session_start", async (_e, c) => start(c));
  pi.on("session_tree", async (_e, c) => start(c));

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

  pi.registerCommand("prs", {
    description: "Session PR box: reopen it, or add <url> | rm <url|#n>",
    handler: async (args, c) => {
      const [sub, arg] = args.trim().split(/\s+/);
      if (!sub) return box(["reopen"]);
      if (sub === "add") {
        if (!arg || !extractUrls(arg).length || urls.includes(arg)) {
          return c.ui.notify("Usage: /prs add <PR url> (not already tracked)", "error");
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
      c.ui.notify("Usage: /prs [add <url> | rm <url|#n>]", "error");
    },
  });
}
