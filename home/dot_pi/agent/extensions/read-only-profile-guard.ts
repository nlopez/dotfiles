/**
 * Read-Only Profile Guard
 *
 * Hard-blocks any tool call that would use a cloud profile whose name does
 * not end in "read-only". Covers:
 *
 *   bash  — AWS_PROFILE / AWS_DEFAULT_PROFILE env var assignments
 *           and --profile flags for aws, terraform, tofu, terragrunt, etc.
 *   write — profile = "..." in .tf / .hcl / .tfvars files
 *   edit  — same, inside newText hunks
 */

import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

const REQUIRED_SUFFIX = "read-only";

// ── regex patterns ──────────────────────────────────────────────────────────

// AWS_PROFILE=value  or  export AWS_PROFILE=value  (quoted or bare)
const ENV_PROFILE_RE =
  /\bAWS_(?:DEFAULT_)?PROFILE=["']?([^"'\s;|&)]+)["']?/g;

// --profile value  or  --profile=value  (any cloud CLI)
const FLAG_PROFILE_RE = /--profile[= ]["']?([^"'\s;|&)]+)["']?/g;

// profile = "value"  or  profile = 'value'  (HCL / .tfvars)
const HCL_PROFILE_RE = /\bprofile\s*=\s*["']([^"']+)["']/g;

// File extensions that may carry HCL profile references
const CLOUD_FILE_RE = /\.(tf|hcl|tfvars)$/i;

// ── helpers ─────────────────────────────────────────────────────────────────

function allMatches(text: string, ...patterns: RegExp[]): string[] {
  const results: string[] = [];
  for (const re of patterns) {
    re.lastIndex = 0;
    let m: RegExpExecArray | null;
    while ((m = re.exec(text)) !== null) {
      results.push(m[1].replace(/^["']|["']$/g, ""));
    }
  }
  return results;
}

function isReadOnly(profile: string): boolean {
  return profile.toLowerCase().endsWith(REQUIRED_SUFFIX);
}

function violation(profiles: string[]): string {
  const bad = profiles.filter((p) => !isReadOnly(p));
  return bad.length > 0
    ? `non-read-only profile(s): ${bad.map((p) => JSON.stringify(p)).join(", ")}`
    : "";
}

// ── extension ───────────────────────────────────────────────────────────────

export default function (pi: ExtensionAPI) {
  pi.on("tool_call", async (event, ctx) => {
    // bash ── scan the shell command for env vars and --profile flags
    if (event.toolName === "bash") {
      const command = (event.input as { command: string }).command ?? "";
      const v = violation(allMatches(command, ENV_PROFILE_RE, FLAG_PROFILE_RE));
      if (v) {
        const reason = `Blocked: ${v}. Only profiles ending in "read-only" are permitted.`;
        ctx.ui.notify(reason, "warning");
        return { block: true, reason };
      }
    }

    // write ── scan new file content for HCL profile references
    if (event.toolName === "write") {
      const { path, content } = event.input as { path: string; content: string };
      if (CLOUD_FILE_RE.test(path)) {
        const v = violation(allMatches(content, HCL_PROFILE_RE));
        if (v) {
          const reason = `Blocked write to ${path}: ${v}. Only profiles ending in "read-only" are permitted.`;
          ctx.ui.notify(reason, "warning");
          return { block: true, reason };
        }
      }
    }

    // edit ── scan newText hunks for HCL profile references
    if (event.toolName === "edit") {
      const { path, edits } = event.input as {
        path: string;
        edits: Array<{ oldText: string; newText: string }>;
      };
      if (CLOUD_FILE_RE.test(path)) {
        const newTexts = (edits ?? []).map((e) => e.newText).join("\n");
        const v = violation(allMatches(newTexts, HCL_PROFILE_RE));
        if (v) {
          const reason = `Blocked edit to ${path}: ${v}. Only profiles ending in "read-only" are permitted.`;
          ctx.ui.notify(reason, "warning");
          return { block: true, reason };
        }
      }
    }

    return undefined;
  });
}
