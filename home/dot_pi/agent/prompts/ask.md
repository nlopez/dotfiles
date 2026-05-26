---
description: Thoroughly research a question and present findings without implementing anything
argument-hint: "[your question]"
---

Research the following question thoroughly and present your findings:

$ARGUMENTS

## Research approach

1. **Deep exploration** – Read all relevant files, docs, config, and code. Use `grep`, `find`, and file reads to build a complete picture. Read linked docs and cross-references.
2. **Synthesis** – Organize what you found into a clear, structured answer. Prioritize accuracy over brevity.
3. **Clarifying questions** – After presenting the answer, explicitly list any uncertainties, ambiguities, or assumptions from the original ask. Ask the user to clarify anything that would change your conclusions.

## Rules

- **Only present information.** Do not write, edit, or propose code changes. Do not suggest implementations.
- Do not scaffold files, create diffs, or generate boilerplate.
- If the question has no single right answer, present the trade-offs and let the user decide.
- Cite the specific files, lines, or sections you referenced.
- If you cannot answer with confidence, say so and explain what additional information you need.
