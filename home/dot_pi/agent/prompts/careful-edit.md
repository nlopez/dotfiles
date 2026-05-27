---
description: Enter careful-edit mode for surgical or refactor-heavy file changes
argument-hint: "[task description]"
---

You are entering **careful-edit mode** for the following task:

$ARGUMENTS

Pi's `edit` tool fails when `oldText` does not match the file's current bytes exactly (after fuzzy normalization of line endings, trailing whitespace, smart quotes, and Unicode dashes). The failures cluster around stale file views, oversized `oldText`, and uncertain indentation. Follow this workflow strictly:

## Workflow

1. **Re-read every target file in this turn.** Do not trust file content from earlier in the session. For large files, use `offset`/`limit` to read only the regions you will touch. If the session was compacted, this is mandatory.
2. **Plan the edits before issuing any.** List, in order:
   - Each file you will modify
   - Each distinct region within that file
   - The intended `oldText` anchor (a short, unique snippet — ideally 1–5 lines)
   - The replacement
3. **Group disjoint changes per file.** Use a single `edit` call with multiple `edits[]` entries for separate regions in the same file. Do not chain several `edit` calls when one will do.
4. **Keep each `oldText` minimal and unique.** 1–5 lines. Anchor on content, not indentation — fuzzy match strips trailing whitespace but not leading whitespace.
5. **One retry rule.** If an `edit` fails with "Could not find the exact text":
   - Stop. Do not retry the same `oldText`.
   - Re-`read` the affected region.
   - Issue a corrected edit with a fresh anchor.
6. **Escalate to `write` when the change is structural.** If a file needs >3 distinct edits, or you are reorganizing imports/sections/layout, rewrite the whole file with `write` instead.
7. **Verify after each file.** After edits land, `read` the changed region back to confirm the result matches intent before moving on.

## Rules

- No speculative edits. If you are unsure of the exact current text, `read` first.
- No bundling unrelated tasks into one edit pass. Finish the named task only.
- For chezmoi-managed files, resolve `chezmoi source-path` first and edit the source — never the destination.
- Report at the end: which files changed, how many `edit` calls succeeded on first try, and any region that required `write` fallback.
