## Research and Uncertainty Protocol

When you are uncertain about something, or when official documentation and best practices would help you make a better decision, **you must search for authoritative sources before guessing**.

### When to search

- You are unsure about a library's API, configuration, or behavior
- You want to follow current best practices for a task
- You are working with unfamiliar code, tools, or frameworks
- You need to verify how something works rather than assume
- The user asks for recommendations or guidance on how to do something

### How to search

1. **Start with web search** for official docs, release notes, and community best practices. Prefer official documentation over third-party blog posts.
2. **Use the `gh` CLI for GitHub sources** — repos, issues, pull requests, and GitHub-hosted docs. Examples:
   - `gh search issues "topic" --repo owner/repo` — find related issues
   - `gh api repos/owner/repo/git/trees/main --jq '.tree[] | select(.path | contains("config"))'` — explore repo structure
   - `gh search code "pattern" --repo owner/repo` — find code patterns in repos
   - `gh repo view owner/repo` — get repo overview and README
3. **Use `fetch_content` for URL-level access** — e.g. GitHub repo pages, documentation sites, or blog posts with deeper context.

### Key principle

**When in doubt, search it out.** It is better to take a moment to find authoritative guidance than to guess and produce a suboptimal or incorrect solution. Always cite your sources when referencing docs or guidance you looked up.
