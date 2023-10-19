alias _command="command -v $1 >/dev/null 2>&1"

# path construction - https://zsh.sourceforge.io/Guide/zshguide02.html#l24
function prepend_path() {
  path=("$1" $path)
}
typeset -aU path
prepend_path ~/bin
prepend_path "${HOME}/.local/bin"
prepend_path "/Applications/Docker.app/Contents/Resources/bin"

export XDG_CONFIG_HOME="${HOME}/.config"


if [[ "$(/usr/bin/uname -m)" == "arm64" ]]; then
  BREW_PREFIX="/opt/homebrew"
else
  BREW_PREFIX="/usr/local"
fi

if [ -d "$BREW_PREFIX" ]; then
  eval "$($BREW_PREFIX/bin/brew shellenv)"

  # use gnu utils with regular names
  if _command greadlink; then
    prepend_path "$BREW_PREFIX/opt/coreutils/libexec/gnubin"
    export MANPATH="$BREW_PREFIX/opt/coreutils/libexec/gnuman:$MANPATH"
  fi
  if _command gsed; then
    prepend_path "$BREW_PREFIX/opt/gnu-sed/libexec/gnubin"
    export MANPATH="$BREW_PREFIX/opt/gnu-sed/libexec/gnuman:$MANPATH"
  fi
  if _command gfind; then
    prepend_path "$BREW_PREFIX/opt/findutils/libexec/gnubin"
    export MANPATH="$BREW_PREFIX/opt/findutils/libexec/gnuman:$MANPATH"
  fi
  if _command gtar; then
    prepend_path "$BREW_PREFIX/opt/gnu-tar/libexec/gnubin"
    export MANPATH="$BREW_PREFIX/opt/gnu-tar/libexec/gnuman:$MANPATH"
  fi
  if [ -f $BREW_PREFIX/opt/gnu-getopt/bin/getopt ]; then
    prepend_path "$BREW_PREFIX/opt/gnu-getopt/bin"
  fi
fi

prepend_path "${BREW_PREFIX}/opt/curl/bin"
prepend_path "${BREW_PREFIX}/opt/openjdk/bin"

alias dotfiles='git --git-dir=$HOME/dotfiles/ --work-tree=$HOME'

# http://matthew-brett.github.io/pydagogue/installing_on_debian.html
# pip install --user path
if _command python; then
  PY_USER_BIN=$(python -c 'import site; print(site.USER_BASE + "/bin")')
  export PY_USER_BIN
  prepend_path $PY_USER_BIN
fi

FPATH="$HOME/.zfunctions:$FPATH"

# Enable Ctrl-x-e to edit command line
autoload -U edit-command-line
zle -N edit-command-line
bindkey '^xe' edit-command-line
bindkey '^x^e' edit-command-line

# Prompt
autoload -Uz promptinit
promptinit
# zstyle ':prompt:pure:prompt:success' color default
# zstyle ':prompt:pure:prompt:failure' color red

# kube-ps1
if [ -n "$BREW_PREFIX" ]; then
  kube_ps1_sh="$BREW_PREFIX/opt/kube-ps1/share/kube-ps1.sh"
fi
if [ -f "$kube_ps1_sh" ] >/dev/null 2>&1; then
  source "$kube_ps1_sh"
fi

if ! _command kube_ps1; then kube_ps1() {}; fi

prompt pure
PROMPT='%(?.%F{magenta}.%F{red}❯%F{magenta})❯%f '
PROMPT='%F{default}%* '$PROMPT
precmd_pipestatus() {
  if [ "$TMUX" != "" ]; then
    tmux rename-window "$(basename $PWD)"
  fi
	RPROMPT="${(j.|.)pipestatus} $(kube_ps1)"
       if [[ ${(j.|.)pipestatus} = 0 ]]; then
              RPROMPT="$(kube_ps1)"
       fi
}
add-zsh-hook precmd precmd_pipestatus

# Completion

if [ -n "$BREW_PREFIX" ]; then
  FPATH=$BREW_PREFIX/share/zsh-completions:$BREW_PREFIX/share/zsh/site-functions:$FPATH
fi
autoload -Uz compinit bashcompinit
compinit
bashcompinit

# Cribbed from https://github.com/ohmyzsh/ohmyzsh/blob/fd786291bab7468c7cdd5066ac436218a1fba9e2/lib/completion.zsh#L61-L73
# terminfo, echoti are zsh builtins
# %F{red}red text%f is also provided by zsh https://scriptingosx.com/2019/07/moving-to-zsh-06-customizing-the-zsh-prompt/
expand-or-complete-with-dots() {
  # toggle line-wrapping off and back on again
  # shellcheck disable=SC2154
  [[ -n "${terminfo[rmam]}" && -n "${terminfo[smam]}" ]] && echoti rmam
  print -Pn "%{%F{red}...%f%}"
  [[ -n "${terminfo[rmam]}" && -n "${terminfo[smam]}" ]] && echoti smam

  zle expand-or-complete
  zle redisplay
}
zle -N expand-or-complete-with-dots
bindkey "^I" expand-or-complete-with-dots

# Case-insensitive matching
zstyle ':completion:*' matcher-list '' 'm:{a-zA-Z}={A-Za-z}' 'r:|[._-]=* r:|=*' 'l:|=* r:|=*'
# Use completion menu
zstyle ':completion:*' menu select

_complete_alias() {
    [[ -n $PREFIX ]] && compadd -- ${(M)${(k)galiases}:#$PREFIX*}
    return 1
}
zstyle ':completion:*' completer _complete_alias _complete _ignored

# Correction
setopt correct

# Abbreviations
typeset -Ag abbrevs
abbrevs=(
  'tfinit' 'terraform init'
  'tfplan' 'terraform plan'
  'tfshow' 'terraform show tfplan'
  'g' 'git'
  'gup' 'git pull --prune --rebase'
  'gst' 'git status'
  'gs' 'git status'
  'gc' 'git commit'
  'grhh' 'git reset --hard HEAD'
  'gp' 'git push'
  'gcd' 'git checkout "$(gh repo view --json defaultBranchRef --jq .defaultBranchRef.name)"'
  'gcp' 'git checkout -'
)

for abbr in ${(k)abbrevs}; do
   alias $abbr="${abbrevs[$abbr]}"
done

magic-abbrev-expand() {
  local MATCH
  LBUFFER=${LBUFFER%%(#m)[_a-zA-Z0-9]#}
  command=${abbrevs[$MATCH]}
  LBUFFER+=${command:-$MATCH}

  if [[ "${command}" =~ "__CURSOR__" ]]; then
    RBUFFER=${LBUFFER[(ws:__CURSOR__:)2]}
    LBUFFER=${LBUFFER[(ws:__CURSOR__:)1]}
  else
    zle self-insert
  fi
}

magic-abbrev-expand-and-execute() {
  magic-abbrev-expand
  zle backward-delete-char
  zle accept-line
}

no-magic-abbrev-expand() {
  LBUFFER+=' '
}

zle -N magic-abbrev-expand
zle -N magic-abbrev-expand-and-execute
zle -N no-magic-abbrev-expand

bindkey " " magic-abbrev-expand
bindkey "^M" magic-abbrev-expand-and-execute
bindkey "^x " no-magic-abbrev-expand
bindkey -M isearch " " self-insert

# Editor
if _command code; then
  export EDITOR="code --add --wait"
  alias e="code --add"
fi

# Misc aliases
_command brew && alias brewup="brew update && brew upgrade && brew cleanup"
alias reload="exec \$SHELL"
# alias k9s="k9s --logoless"
alias dec2hex='printf "%x\n"'
alias jcurl="curl --output /dev/null --silent --show-error --write-out '%{json}'"
alias history="history -D -E -t '%Y-%m-%d %H:%M:%S %Z'"

# Misc
setopt cdablevars
setopt extendedglob

# History
export HISTFILE="$HOME/.zsh_history"
export HISTSIZE=10000000
export SAVEHIST=$HISTSIZE
setopt BANG_HIST                 # Treat the '!' character specially during expansion.
setopt EXTENDED_HISTORY          # Write the history file in the ":start:elapsed;command" format.
setopt INC_APPEND_HISTORY        # Write to the history file immediately, not when the shell exits.
setopt SHARE_HISTORY             # Share history between all sessions.
setopt HIST_EXPIRE_DUPS_FIRST    # Expire duplicate entries first when trimming history.
setopt HIST_IGNORE_DUPS          # Don't record an entry that was just recorded again.
setopt HIST_IGNORE_ALL_DUPS      # Delete old recorded entry if new entry is a duplicate.
setopt HIST_FIND_NO_DUPS         # Do not display a line previously found.
setopt HIST_IGNORE_SPACE         # Don't record an entry starting with a space.
setopt HIST_SAVE_NO_DUPS         # Don't write duplicate entries in the history file.
setopt HIST_REDUCE_BLANKS        # Remove superfluous blanks before recording entry.
setopt HIST_VERIFY               # Don't execute immediately upon history expansion.
setopt HIST_BEEP                 # Beep when accessing nonexistent history.

# pushd
setopt autopushd pushdminus pushdsilent pushdtohome pushdignoredups
alias dh='dirs -v'
export DIRSTACKSIZE=10

# direnv
if _command direnv; then eval "$(direnv hook zsh)"; fi

# rbenv
if _command rbenv; then
  prepend_path "$HOME/.rbenv/plugins/ruby-build/bin"
  prepend_path "$HOME/.rbenv/bin"
  eval "$(rbenv init -)"
fi

export GEM_HOME="$HOME/.local"

if [ -d "$HOME/src" ]; then
  CDPATH=".:$(find ~/src -mindepth 2 -maxdepth 2 -type d -printf "%p:" | sed 's/:$//g')"
  export CDPATH
fi

_command dircolors && eval "$(dircolors "$HOME/.dir_colors")"
alias ls="ls -lFAh --group-directories-first --color=always"
alias -g groot="$(git rev-parse --show-toplevel)"

if [ -f "/usr/local/bin/aws_zsh_completer.sh" ]; then
  source "/usr/local/bin/aws_zsh_completer.sh"
fi

# GOROOT-based install location
if _command go; then
  prepend_path /usr/local/opt/go/libexec/bin
  prepend_path "$(go env GOPATH)/bin"
  export PATH
fi

# Rust
# shellcheck source=./.cargo/env
if [ -f "$HOME/.cargo/env" ]; then source "$HOME/.cargo/env"; fi

# Keychain
if _command keychain; then eval "$(keychain --eval --quiet --inherit any)"; fi

# Homebrew curl
if [ -f "${BREW_PREFIX}/opt/curl/bin/curl" ]; then prepend_path "${BREW_PREFIX}/opt/curl/bin/curl"; fi

# https://unix.stackexchange.com/a/377765
# known hosts completion
zstyle -e ':completion:*:(ssh|scp|sftp|rsh|rsync):hosts' hosts 'reply=(${=${${(f)"$(cat {/etc/ssh_,~/.ssh/known_}hosts(|2)(N) /dev/null)"}%%[# ]*}//,/ })'

# What do I look like, a guy who's not lazy?
if _command kubectl; then
  source <(kubectl completion zsh)
  alias k=kubectl
  alias kd='kubectl describe'
  alias kdp='kubectl describe pod'
  alias kg='kubectl get'
  alias kgp='kubectl get pod'
  alias ke='kubectl exec -it'
fi

_command kubectx && alias kctx=kubectx
_command kubens && alias kns=kubens
_command aws_vault && eval "$(aws-vault --completion-script-zsh)"


# shellcheck source=./.zshrc_work
if [ -f "$HOME/.zshrc_work" ]; then source "$HOME/.zshrc_work"; fi

# serverless
# tabtab source for packages
# uninstall by removing these lines
[[ -f ~/.config/tabtab/__tabtab.zsh ]] && . ~/.config/tabtab/__tabtab.zsh || true

if [ -d  "/usr/local/Caskroom/google-cloud-sdk/latest/google-cloud-sdk" ]; then
  source /usr/local/Caskroom/google-cloud-sdk/latest/google-cloud-sdk/completion.zsh.inc
  source /usr/local/Caskroom/google-cloud-sdk/latest/google-cloud-sdk/path.zsh.inc
fi

_command saml2aws && eval "$(saml2aws --completion-script-zsh)"
_command pipx && eval "$(register-python-argcomplete pipx)"

[ -f ~/.fzf.zsh ] && source ~/.fzf.zsh
export FZF_TMUX=1

export WORDCHARS=""

source "$BREW_PREFIX/opt/asdf/libexec/asdf.sh" 2>/dev/null || true

if _command pyenv; then
  export PYENV_ROOT="$HOME/.pyenv"
  command -v pyenv >/dev/null || prepend_path "$PYENV_ROOT/bin"
  eval "$(pyenv init -)"
fi

# krew
if [ -d "$HOME/.krew/bin" ] || [ -n "$KREW_ROOT" ]; then
  prepend_path "${KREW_ROOT:-$HOME/.krew}/bin"
fi

export PATH="/opt/homebrew/opt/binutils/bin:$PATH"
export LESS="--raw-control-chars --quit-if-one-screen"
export LESSCHARSET="utf-8"
export MANPAGER="less --use-color -Dd+r -Du+b"
export MANROFFOPT="-P -c"
export PAGER="less"

# https://github.com/zsh-users/zsh-autosuggestions
export ZSH_AUTOSUGGEST_USE_ASYNC=true
source "$BREW_PREFIX/share/zsh-autosuggestions/zsh-autosuggestions.zsh" 2>/dev/null || true
bindkey '^ ' autosuggest-acceptx

# https://github.com/zsh-users/zsh-syntax-highlighting
# Keep this last! https://github.com/zsh-users/zsh-syntax-highlighting#why-must-zsh-syntax-highlightingzsh-be-sourced-at-the-end-of-the-zshrc-file
source "$BREW_PREFIX/share/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh" 2>/dev/null || true
