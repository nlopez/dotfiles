# local bin paths
export PATH="/usr/local/bin:$PATH"
export PATH="/usr/local/sbin:$PATH"
export PATH="$HOME/.local/bin:$PATH"

alias dotfiles='git --git-dir=$HOME/dotfiles/ --work-tree=$HOME'

if command -v pyenv >/dev/null 2>&1; then eval "$(pyenv init -)"; fi

# http://matthew-brett.github.io/pydagogue/installing_on_debian.html
# pip install --user path
PY_USER_BIN=$(python -c 'import site; print(site.USER_BASE + "/bin")')
export PY_USER_BIN
export PATH=$PY_USER_BIN:$PATH

# use gnu utils with regular names
if command -v greadlink >/dev/null 2>&1; then
  export PATH="/usr/local/opt/coreutils/libexec/gnubin:$PATH"
  export MANPATH="/usr/local/opt/coreutils/libexec/gnuman:$MANPATH"
fi
if command -v gsed >/dev/null 2>&1; then
  export PATH="/usr/local/opt/gnu-sed/libexec/gnubin:$PATH"
  export MANPATH="/usr/local/opt/gnu-sed/libexec/gnuman:$MANPATH"
fi
if command -v gfind >/dev/null 2>&1; then
  export PATH="/usr/local/opt/findutils/libexec/gnubin:$PATH"
  export MANPATH="/usr/local/opt/findutils/libexec/gnuman:$MANPATH"
fi
if command -v gtar >/dev/null 2>&1; then
  export PATH="/usr/local/opt/gnu-tar/libexec/gnubin:$PATH"
  export MANPATH="/usr/local/opt/gnu-tar/libexec/gnuman:$MANPATH"
fi
if [ -f /usr/local/opt/gnu-getopt/bin/getopt ]; then
  export PATH="/usr/local/opt/gnu-getopt/bin:$PATH"
fi

# Enable Ctrl-x-e to edit command line
autoload -U edit-command-line
zle -N edit-command-line
bindkey '^xe' edit-command-line
bindkey '^x^e' edit-command-line

# fpath can't be quoted
# shellcheck disable=SC2206
fpath=(
  "$HOME/.zfunctions"
  /usr/local/share/zsh/site-functions
  $fpath
)

# Prompt
autoload -Uz promptinit
promptinit
prompt pure

# Completion
autoload -Uz compinit
compinit
#bashcompinit

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

# Correction
setopt correct

# git
alias g=git
alias gup="git pull --rebase"
alias gst="git status --ignored"
alias gc="git commit"
alias grhh="git reset --hard HEAD"
alias gp="git push"

# Editor
export EDITOR="code --add --wait"
alias e="code --add"

# Misc aliases
alias brewup="brew update && brew upgrade && brew cleanup"
alias reload="exec \$SHELL"

# Misc
setopt cdablevars
setopt extendedglob

# History
export HISTSIZE=500000
export HISTFILE="$HOME/.history"
export SAVEHIST=$HISTSIZE
setopt hist_ignore_all_dups
setopt hist_ignore_space
setopt share_history
setopt hist_verify
setopt hist_no_store

# pushd
setopt autopushd pushdminus pushdsilent pushdtohome pushdignoredups
alias dh='dirs -v'
export DIRSTACKSIZE=10

# direnv
if command -v direnv >/dev/null 2>&1; then eval "$(direnv hook zsh)"; fi

# rbenv
if command -v rbenv >/dev/null 2>&1; then
  export PATH="$HOME/.rbenv/plugins/ruby-build/bin:$PATH"
  export PATH="$HOME/.rbenv/bin:$PATH"
  eval "$(rbenv init -)"
fi

export GEM_HOME="$HOME/.local"

# kubectl
if command -v kubectl >/dev/null 2>&1; then
  eval "$(kubectl completion zsh)"
  autoload -U colors
  colors
  # shellcheck source=./.zfunctions/kubectl.zsh
  source "$HOME/.zfunctions/kubectl.zsh"
fi

CDPATH=".:$(find ~/src -mindepth 2 -maxdepth 2 -type d -printf "%p:" | sed 's/:$//g')"
export CDPATH

if command -v dircolors >/dev/null 2>&1; then
  eval "$(dircolors "$HOME/.dir_colors")"
fi
alias ls="ls -lFAh --group-directories-first --color=always"

if [ -f "/usr/local/bin/aws_zsh_completer.sh" ]; then
  source "/usr/local/bin/aws_zsh_completer.sh"
fi

export PATH="$PATH:$HOME/bin"
export LESSCHARSET=utf-8

# GOROOT-based install location
if command -v go >/dev/null 2>&1; then
  export PATH=$PATH:/usr/local/opt/go/libexec/bin
  PATH="$PATH:$(go env GOPATH)/bin"
  export PATH
fi

# Rust
# shellcheck source=./.cargo/env
if [ -f "$HOME/.cargo/env" ]; then source "$HOME/.cargo/env"; fi

# Keychain
if command -v keychain >/dev/null 2>&1; then eval "$(keychain --eval --quiet --inherit any ~/.ssh/id_*)"; fi

# https://unix.stackexchange.com/a/377765
# known hosts completion
zstyle -e ':completion:*:(ssh|scp|sftp|rsh|rsync):hosts' hosts 'reply=(${=${${(f)"$(cat {/etc/ssh_,~/.ssh/known_}hosts(|2)(N) /dev/null)"}%%[# ]*}//,/ })'

# https://github.com/zsh-users/zsh-autosuggestions
export ZSH_AUTOSUGGEST_USE_ASYNC=true
source "/usr/local/share/zsh-autosuggestions/zsh-autosuggestions.zsh" 2>/dev/null || true
bindkey '^ ' autosuggest-acceptx

# shellcheck source=./.zshrc_work
if [ -f "$HOME/.zshrc_work" ]; then source "$HOME/.zshrc_work"; fi

# https://github.com/zsh-users/zsh-syntax-highlighting
# Keep this last! https://github.com/zsh-users/zsh-syntax-highlighting#why-must-zsh-syntax-highlightingzsh-be-sourced-at-the-end-of-the-zshrc-file
source "/usr/local/share/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh" 2>/dev/null || true
