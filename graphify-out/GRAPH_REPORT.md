# Graph Report - .  (2026-05-08)

## Corpus Check
- 6 files · ~8,899 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 19 nodes · 27 edges · 8 communities detected
- Extraction: 70% EXTRACTED · 30% INFERRED · 0% AMBIGUOUS · INFERRED: 8 edges (avg confidence: 0.8)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Community 3|Community 3]]
- [[_COMMUNITY_Community 4|Community 4]]
- [[_COMMUNITY_Community 5|Community 5]]
- [[_COMMUNITY_Community 6|Community 6]]
- [[_COMMUNITY_Community 7|Community 7]]

## God Nodes (most connected - your core abstractions)
1. `main()` - 5 edges
2. `main()` - 5 edges
3. `render_and_lint()` - 5 edges
4. `build_data()` - 4 edges
5. `render_template()` - 4 edges
6. `print_verbose()` - 4 edges
7. `render_and_check()` - 4 edges
8. `run_shellcheck()` - 4 edges
9. `chezmoi_root()` - 3 edges
10. `lint_json()` - 3 edges

## Surprising Connections (you probably didn't know these)
- `chezmoi_root()` --calls--> `main()`  [INFERRED]
  scripts/chezmoi_lib.py → scripts/shellcheck.py
- `chezmoi_root()` --calls--> `main()`  [INFERRED]
  scripts/chezmoi_lib.py → scripts/jsonlint.py
- `build_data()` --calls--> `main()`  [INFERRED]
  scripts/chezmoi_lib.py → scripts/shellcheck.py
- `build_data()` --calls--> `main()`  [INFERRED]
  scripts/chezmoi_lib.py → scripts/jsonlint.py
- `render_template()` --calls--> `render_and_check()`  [INFERRED]
  scripts/chezmoi_lib.py → scripts/shellcheck.py

## Communities

### Community 0 - "Community 0"
Cohesion: 0.5
Nodes (3): chezmoi_root(), print_verbose(), Print verbose output with OS and user configuration.

### Community 1 - "Community 1"
Cohesion: 1.0
Nodes (3): main(), render_and_check(), run_shellcheck()

### Community 2 - "Community 2"
Cohesion: 1.0
Nodes (3): lint_json(), main(), render_and_lint()

### Community 3 - "Community 3"
Cohesion: 1.0
Nodes (2): build_data(), Build override and user data for template rendering.

### Community 4 - "Community 4"
Cohesion: 1.0
Nodes (2): Render a chezmoi template file, returning (output, error)., render_template()

### Community 5 - "Community 5"
Cohesion: 1.0
Nodes (0): 

### Community 6 - "Community 6"
Cohesion: 1.0
Nodes (0): 

### Community 7 - "Community 7"
Cohesion: 1.0
Nodes (0): 

## Knowledge Gaps
- **3 isolated node(s):** `Build override and user data for template rendering.`, `Render a chezmoi template file, returning (output, error).`, `Print verbose output with OS and user configuration.`
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 3`** (2 nodes): `build_data()`, `Build override and user data for template rendering.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 4`** (2 nodes): `Render a chezmoi template file, returning (output, error).`, `render_template()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 5`** (1 nodes): `symlink_Microsoft.VSCode_profile.ps1`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 6`** (1 nodes): `symlink_Microsoft.PowerShell_profile.ps1`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 7`** (1 nodes): `symlink_Microsoft.PowerShell.VSCode_profile.ps1`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `render_template()` connect `Community 4` to `Community 0`, `Community 1`, `Community 2`?**
  _High betweenness centrality (0.136) - this node is a cross-community bridge._
- **Why does `print_verbose()` connect `Community 0` to `Community 1`, `Community 2`?**
  _High betweenness centrality (0.136) - this node is a cross-community bridge._
- **Why does `render_and_lint()` connect `Community 2` to `Community 0`, `Community 4`?**
  _High betweenness centrality (0.135) - this node is a cross-community bridge._
- **Are the 2 inferred relationships involving `main()` (e.g. with `chezmoi_root()` and `build_data()`) actually correct?**
  _`main()` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `main()` (e.g. with `chezmoi_root()` and `build_data()`) actually correct?**
  _`main()` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `render_and_lint()` (e.g. with `print_verbose()` and `render_template()`) actually correct?**
  _`render_and_lint()` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `build_data()` (e.g. with `main()` and `main()`) actually correct?**
  _`build_data()` has 2 INFERRED edges - model-reasoned connections that need verification._