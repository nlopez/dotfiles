---
description: Think through a task and produce a step-by-step plan before coding
argument-hint: "[task description]"
---

Before writing any code, produce a clear, structured plan for the following task:

$ARGUMENTS

Follow this process:

1. **Understand** – Restate the goal in your own words. Identify any ambiguities and state your assumptions explicitly.
2. **Explore** – Read the relevant files, grep for key symbols, and build a mental model of the existing code. List every file you will need to touch and why.
3. **Design** – Describe the approach at a high level. Call out alternatives you considered and why you are not choosing them.
4. **Steps** – Break the work into ordered, atomic steps. Each step should be small enough to verify independently.
5. **Risks & edge cases** – Identify anything that could go wrong, any backward-compatibility concerns, and how you will handle them.
6. **Open questions** – List anything you need the user to clarify before proceeding.

Output the plan in Markdown. Do **not** write any code yet — wait for confirmation before proceeding.
