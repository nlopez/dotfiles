# git worktree helpers — repo-root-aware
#
# Convention (established by `dolly`):
#   ~/src/<host>/<repo>/.bare    ← bare clone
#   ~/src/<host>/<repo>/.git     ← "gitdir: ./.bare"
#   ~/src/<host>/<repo>/default  ← symlink → default branch worktree
#   ~/src/<host>/<repo>/<wt>/    ← worktrees
#
# `git rev-parse --git-common-dir` returns the absolute path to .bare from
# anywhere inside the tree (repo root or any worktree subdirectory).
# Its parent is the directory that should contain all worktrees.
#
# This also works for plain (non-bare) repos: --git-common-dir returns the
# .git directory, so its parent is the repo root — no behavioural change there.

_gw_root() {
  local common
  common=$(git rev-parse --git-common-dir 2>/dev/null) || return 1
  # git may return a relative path for non-worktree repos; make it absolute.
  [[ "$common" != /* ]] && common="${PWD}/${common}"
  # Normalize (no realpath needed — just resolve . and ..)
  common=$(cd -- "$common" && pwd) || return 1
  # Parent of .bare (or .git) is the worktree root.
  print -r -- "${common:h}"
}

# gwa <path> [<branch>]  — add a new worktree at <repo-root>/<path>
gwa() {
  local root
  root=$(_gw_root) || return 1
  # When called with a single bare path, force the branch name to the full
  # path so that remote-tracking (--guess-remote / worktree.guessRemote)
  # resolves origin/name/like/this instead of just origin/this.
  if [[ $# -eq 1 && "$1" != -* ]]; then
    git -C "$root" worktree add -b "$1" "$1"
  else
    git -C "$root" worktree add "$@"
  fi
}

# gwl [options]  — list worktrees relative to repo root
gwl() {
  local root
  root=$(_gw_root) || return 1
  git -C "$root" worktree list "$@"
}

# gwr <worktree>  — remove a worktree by name/path
gwr() {
  local root
  root=$(_gw_root) || return 1
  git -C "$root" worktree remove "$@"
}

# gwm <worktree> <new-path>  — move a worktree
gwm() {
  local root
  root=$(_gw_root) || return 1
  git -C "$root" worktree move "$@"
}
