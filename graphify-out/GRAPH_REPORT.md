# Graph Report - chezmoi  (2026-05-17)

## Corpus Check
- 20 files · ~17,329 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 207 nodes · 255 edges · 22 communities (19 shown, 3 thin omitted)
- Extraction: 91% EXTRACTED · 9% INFERRED · 0% AMBIGUOUS · INFERRED: 22 edges (avg confidence: 0.7)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `e3b5c17d`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Community 3|Community 3]]
- [[_COMMUNITY_Community 4|Community 4]]
- [[_COMMUNITY_Community 5|Community 5]]
- [[_COMMUNITY_Community 6|Community 6]]
- [[_COMMUNITY_Community 7|Community 7]]
- [[_COMMUNITY_Community 8|Community 8]]
- [[_COMMUNITY_Community 9|Community 9]]
- [[_COMMUNITY_Community 10|Community 10]]
- [[_COMMUNITY_Community 11|Community 11]]
- [[_COMMUNITY_Community 12|Community 12]]
- [[_COMMUNITY_Community 13|Community 13]]
- [[_COMMUNITY_Community 14|Community 14]]
- [[_COMMUNITY_Community 15|Community 15]]

## God Nodes (most connected - your core abstractions)
1. `/graphify` - 16 edges
2. `What You Must Do When Invoked` - 15 edges
3. `build_data()` - 8 edges
4. `render_and_lint()` - 8 edges
5. `Agent Guidelines — Dotfile Management with Chezmoi` - 8 edges
6. `For --update (incremental re-extraction)` - 8 edges
7. `Tmux Status Extension (pi)` - 8 edges
8. `Auto Theme Extension (pi/macOS)` - 8 edges
9. `render_template()` - 7 edges
10. `render_and_check()` - 7 edges

## Surprising Connections (you probably didn't know these)
- `Terraform/HashiCorp Skills Registry` --cross_domain--> `Auto Theme Extension (pi/macOS)`  [INFERRED]
  home/dot_claude/CLAUDE.md → home/dot_pi/agent/extensions/auto-theme.ts
- `Solarized Color Palette` --shares_theme_name--> `Solarized Light Theme`  [INFERRED]
  home/dot_config/k9s/skins/solarized-light.yml → home/dot_pi/agent/extensions/auto-theme.ts
- `Agent Guidelines for Chezmoi` --complements--> `Project README (chezmoi setup)`  [INFERRED]
  AGENTS.md → README.md
- `render_and_lint()` --semantically_similar_to--> `render_and_check()`  [INFERRED] [semantically similar]
  scripts/jsonlint.py → scripts/shellcheck.py
- `Auto Theme Extension (pi/macOS)` --cross_extension--> `Tmux Status Extension (pi)`  [INFERRED]
  home/dot_pi/agent/extensions/auto-theme.ts → home/dot_pi/agent/extensions/tmux-status.ts

## Hyperedges (group relationships)
- **Pi Agent Extensions** — tmux_status_extension, completion_indicator_extension, auto_theme_extension [EXTRACTED 0.90]
- **Chezmoi Linting Ecosystem** — shellcheck_linter, jsonlint_linter, chezmoi_lib_library [EXTRACTED 0.90]
- **Cross-platform Dotfile System** — executable_tfplan_tfplan, executable_aws_aws_shim, executable_tfenv_tfenv_shim, vscode_profile_powershell, windows_powershell_profile, k9s_skin_solarized_light [INFERRED 0.60]
- **Agent Prompt System** — plan_prompt_planner, ask_prompt_researcher, graphify_skill_pi_skill [INFERRED 0.70]

## Communities (22 total, 3 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.07
Nodes (38): code:block1 (/graphify                                             # full), code:bash ($(cat graphify-out/.graphify_python) -c "), code:block26 (Graph complete. Outputs in PATH_TO_DIR/graphify-out/), code:bash (if [ ! -f graphify-out/.graphify_python ]; then), code:bash ($(cat graphify-out/.graphify_python) -c "), code:bash ($(cat graphify-out/.graphify_python) -c "), code:bash ($(cat graphify-out/.graphify_python) -c "), code:bash ($(cat graphify-out/.graphify_python) -c ") (+30 more)

### Community 1 - "Community 1"
Cohesion: 0.09
Nodes (30): code:bash ($(cat graphify-out/.graphify_python) -c "), code:bash (mkdir -p graphify-out), code:bash ($(cat graphify-out/.graphify_python) -c "), code:bash ($(cat graphify-out/.graphify_python) -c "), code:bash ($(cat graphify-out/.graphify_python) -c "), code:bash ($(cat graphify-out/.graphify_python) -c "), code:bash ($(cat graphify-out/.graphify_python) -c "), code:bash ($(cat graphify-out/.graphify_python) -c ") (+22 more)

### Community 2 - "Community 2"
Cohesion: 0.14
Nodes (23): build_data(), chezmoi_root(), Chezmoi Library (Python), Cross-OS Support (darwin/linux/windows), print_verbose(), Build override and user data for template rendering., Render a chezmoi template file, returning (output, error)., Print verbose output with OS and user configuration. (+15 more)

### Community 3 - "Community 3"
Cohesion: 0.1
Nodes (20): Adding a new dotfile, Agent Guidelines — Dotfile Management with Chezmoi, code:sh (# Install chezmoi), code:sh (chezmoi source-path       # Show the source file for a given), code:gotemplate ({{- if eq .chezmoi.os "darwin" -}}), code:gotemplate ({{ .mydata.key }}), code:block5 (.chezmoiscripts/), code:sh (# Lint all JSON templates (renders for darwin/linux/windows)) (+12 more)

### Community 4 - "Community 4"
Cohesion: 0.13
Nodes (17): Atom One Dark Theme, Edge Confidence Audit Trail (EXTRACTED/INFERRED/AMBIGUOUS), macOS Dark/Light Mode Detection, Auto Theme Extension (pi/macOS), macOS-only Platform Guard, Double-read Theme Confirmation, Periodic Theme Polling (2s), Claude Skill Registry (graphify + Terraform) (+9 more)

### Community 5 - "Community 5"
Cohesion: 0.2
Nodes (14): SSO Auth Error Detection, AWS CLI Shadow Wrapper, Lazy Auth Pattern, AWS Profile Detection (CLI env), Real AWS Binary Locator, AWS SSO Auto-login, Tenv Version Manager, Terraform Version Management (+6 more)

### Community 6 - "Community 6"
Cohesion: 0.23
Nodes (13): Agent-start Hook (reset), Context Message Injector, Completion Indicator Extension (pi), Tool/Char Count Extractor, UI Notification System, Agent-end Hook with Question Detection, Emoji State Machine (🤖/✳️/🛎️), Tmux Status Extension (pi) (+5 more)

### Community 7 - "Community 7"
Cohesion: 0.22
Nodes (10): code:bash ($(cat graphify-out/.graphify_python) -c "), code:bash ($(cat graphify-out/.graphify_python) -c "), code:bash ($(cat graphify-out/.graphify_python) -c "), code:bash ($(cat graphify-out/.graphify_python) -c "), code:block8 ([Agent tool call 1: files 1-15, subagent_type="general-purpo), code:block9 (You are a graphify extraction subagent. Read the files liste), Part A - Structural extraction for code files, Part B - Semantic extraction (parallel subagents) (+2 more)

### Community 8 - "Community 8"
Cohesion: 0.53
Nodes (4): getWindowBase(), notify(), setWindowTitle(), stripWindowEmoji()

### Community 9 - "Community 9"
Cohesion: 0.5
Nodes (4): Knowledge Graph Reference (graphify), No-Implementation Rule (pure research), Deep Research Method (explore/synthesis/clarify), Research/Ask Prompt Template

### Community 13 - "Community 13"
Cohesion: 0.67
Nodes (3): Default PowerShell Profile, VSCode PowerShell Profile, Windows PowerShell Profile

### Community 14 - "Community 14"
Cohesion: 0.67
Nodes (3): Agent Guidelines for Chezmoi, Claude Agent Guidelines for Chezmoi, Project README (chezmoi setup)

### Community 15 - "Community 15"
Cohesion: 0.67
Nodes (3): No-Code-Until-Confirmed Rule, Plan Prompt Template, Structured Planning Method (Understand/Explore/Design/Steps/Risks/Questions)

## Knowledge Gaps
- **59 isolated node(s):** `Build override and user data for template rendering.`, `Render a chezmoi template file, returning (output, error).`, `Print verbose output with OS and user configuration.`, `code:block1 (sh -c "$(curl -fsLS get.chezmoi.io)" -d -b ~/.local/bin -- i)`, `What this repo is` (+54 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **3 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `What You Must Do When Invoked` connect `Community 1` to `Community 0`, `Community 7`?**
  _High betweenness centrality (0.103) - this node is a cross-community bridge._
- **Why does `/graphify` connect `Community 0` to `Community 1`?**
  _High betweenness centrality (0.095) - this node is a cross-community bridge._
- **Why does `Step 3 - Extract entities and relationships` connect `Community 7` to `Community 1`?**
  _High betweenness centrality (0.030) - this node is a cross-community bridge._
- **Are the 3 inferred relationships involving `build_data()` (e.g. with `main()` and `main()`) actually correct?**
  _`build_data()` has 3 INFERRED edges - model-reasoned connections that need verification._
- **Are the 3 inferred relationships involving `render_and_lint()` (e.g. with `print_verbose()` and `render_template()`) actually correct?**
  _`render_and_lint()` has 3 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Build override and user data for template rendering.`, `Render a chezmoi template file, returning (output, error).`, `Print verbose output with OS and user configuration.` to the rest of the system?**
  _59 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.07 - nodes in this community are weakly interconnected._