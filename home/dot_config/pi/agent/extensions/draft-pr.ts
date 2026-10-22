/**
 * draft-pr extension
 *
 * Intercepts any `gh pr create` command and ensures it always includes
 * the --draft flag. Handles absolute paths to gh (e.g. the dogbrew shim),
 * shell variables (`$G pr create`), and gh global flags (`-R owner/repo`).
 * Each invocation is checked separately; if --draft is already present it
 * is left unchanged, otherwise the flag is injected and the user is notified.
 */

import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { createBashTool, isToolCallEventType } from "@earendil-works/pi-coding-agent";

// Matches a `gh pr create` invocation, including:
//   gh pr create ...            /opt/dogbrew/shims/bin/gh pr create ...
//   $G pr create ...            ${GH} pr create ...
//   gh -R owner/repo pr create  gh --repo owner/repo pr create
// Group 1 is everything up to and including `create`.
const PR_CREATE =
  /((?<![\w./$-])(?:[^\s"'`=;&|()<>]*\/)?gh|\$\{?\w+\}?)((?:\s+(?:-R|--repo)(?:\s+|=)\S+|\s+-\S+)*)\s+pr\s+create(?![\w-])/g;

// The invocation ends at an unescaped newline or a shell control operator.
const SEGMENT_END = /(?<!\\)\n|[;&|]/;

export function injectDraft(command: string): string | undefined {
  let changed = false;
  let out = "";
  let last = 0;
  for (const m of command.matchAll(PR_CREATE)) {
    const start = m.index!;
    const afterCreate = start + m[0].length;
    const rest = command.slice(afterCreate);
    const end = rest.search(SEGMENT_END);
    const args = end === -1 ? rest : rest.slice(0, end);
    // Already a draft (long flag, or short flag cluster containing d).
    if (/(?:^|\s)(?:--draft(?:=true)?|-[A-Za-z]*d[A-Za-z]*)(?=\s|$)/.test(args)) continue;
    out += command.slice(last, afterCreate) + " --draft";
    last = afterCreate;
    changed = true;
  }
  if (!changed) return undefined;
  return out + command.slice(last);
}

export default function (pi: ExtensionAPI) {
  // Backstop: rewrite the command at spawn time, after every other hook has
  // run. This also covers bash calls that never pass through `tool_call`.
  const bashTool = createBashTool(process.cwd(), {
    spawnHook: ({ command, cwd, env }) => ({
      command: injectDraft(command) ?? command,
      cwd,
      env,
    }),
  });
  pi.registerTool({
    ...bashTool,
    execute: async (id, params, signal, onUpdate, _ctx) =>
      bashTool.execute(id, params, signal, onUpdate),
  });

  pi.on("tool_call", async (event, ctx) => {
    if (!isToolCallEventType("bash", event)) return;

    const { command } = event.input;
    if (!command) return;

    const updated = injectDraft(command);
    if (!updated) return;

    event.input.command = updated;
    ctx.ui.notify("Injected --draft into gh pr create", "info");
  });
}
