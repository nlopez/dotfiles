/**
 * pr-links extension
 *
 * Rewrites GitHub PR references in each finished assistant message into
 * markdown links: `owner/repo#123` always, bare `#123` against the GitHub
 * `origin` remote of the session's working directory. The rewrite lives in
 * ./linkify.ts, the same file the Claude Code pr-links mod uses.
 */

import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { githubRepoFromRemote, linkifyPrRefs } from "./linkify";

export default function (pi: ExtensionAPI) {
  const repoByCwd = new Map<string, Promise<string | undefined>>();

  function repoFor(cwd: string): Promise<string | undefined> {
    let repo = repoByCwd.get(cwd);
    if (!repo) {
      repo = pi.exec("git", ["remote", "get-url", "origin"], { cwd, timeout: 2000 }).then(
        (r) => (r.code === 0 ? githubRepoFromRemote(r.stdout) : undefined),
        () => undefined,
      );
      repoByCwd.set(cwd, repo);
    }
    return repo;
  }

  pi.on("message_end", async (event, ctx) => {
    const message = event.message;
    if (message.role !== "assistant" || !Array.isArray(message.content)) return;
    if (!message.content.some((part) => part.type === "text" && part.text.includes("#"))) return;

    const repo = await repoFor(ctx.cwd);
    let changed = false;
    const content = message.content.map((part) => {
      if (part.type !== "text") return part;
      const text = linkifyPrRefs(part.text, repo);
      if (text === part.text) return part;
      changed = true;
      return { ...part, text };
    });
    return changed ? { message: { ...message, content } } : undefined;
  });
}
