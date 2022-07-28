alias _command="command -v $1 >/dev/null 2>&1"

# local bin paths
export PATH="/usr/local/bin:$PATH"
export PATH="/usr/local/sbin:$PATH"
export PATH="$HOME/.local/bin:$PATH"

# Know what I hate? Fun.
export ANSIBLE_NOCOWS=1

alias dotfiles='git --git-dir=$HOME/dotfiles/ --work-tree=$HOME'

if _command pyenv; then
  export PYENV_ROOT="$HOME/.pyenv"
  export PATH="$PYENV_ROOT/bin:$PATH"
  eval "$(pyenv init --path)"
  eval "$(pyenv init -)"
fi

# http://matthew-brett.github.io/pydagogue/installing_on_debian.html
# pip install --user path
if _command python; then
  PY_USER_BIN=$(python -c 'import site; print(site.USER_BASE + "/bin")')
  export PY_USER_BIN
  export PATH=$PY_USER_BIN:$PATH
fi

# use gnu utils with regular names
if _command greadlink; then
  export PATH="/usr/local/opt/coreutils/libexec/gnubin:$PATH"
  export MANPATH="/usr/local/opt/coreutils/libexec/gnuman:$MANPATH"
fi
if _command gsed; then
  export PATH="/usr/local/opt/gnu-sed/libexec/gnubin:$PATH"
  export MANPATH="/usr/local/opt/gnu-sed/libexec/gnuman:$MANPATH"
fi
if _command gfind; then
  export PATH="/usr/local/opt/findutils/libexec/gnubin:$PATH"
  export MANPATH="/usr/local/opt/findutils/libexec/gnuman:$MANPATH"
fi
if _command gtar; then
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
zstyle ':prompt:pure:prompt:success' color default
zstyle ':prompt:pure:prompt:failure' color red
prompt pure

kube_ps1_sh="/usr/local/opt/kube-ps1/share/kube-ps1.sh"
if [ -f "$kube_ps1_sh" ] >/dev/null 2>&1; then
  source "$kube_ps1_sh"
  PS1='$(kube_ps1)'$PS1
fi

# Completion
autoload -Uz compinit bashcompinit
compinit
bashcompinit

# Cribbed from https://github.com/ohmyzsh/ohmyzsh/blob/fd786291bab7468c7cdd5066ac436218a1fba9e2/lib/completion.zsh#L61-L73
# terminfo, echoti are zsh builtins
# %F{red}red text%f is also provided by zsh https://scriptingosx.com/2019/07/moving-to-zsh-06-customizing-the-zsh-prompt/
# expand-or-complete-with-dots() {
#   # toggle line-wrapping off and back on again
#   # shellcheck disable=SC2154
#   [[ -n "${terminfo[rmam]}" && -n "${terminfo[smam]}" ]] && echoti rmam
#   print -Pn "%{%F{red}...%f%}"
#   [[ -n "${terminfo[rmam]}" && -n "${terminfo[smam]}" ]] && echoti smam

#   zle expand-or-complete
#   zle redisplay
# }
# zle -N expand-or-complete-with-dots
# bindkey "^I" expand-or-complete-with-dots

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

# git
alias g=git
alias gup="git pull --rebase"
alias gst="git status"
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
# export HISTFILE=/dev/null
# export HISTSIZE=0
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
if _command direnv; then eval "$(direnv hook zsh)"; fi

# rbenv
if _command rbenv; then
  export PATH="$HOME/.rbenv/plugins/ruby-build/bin:$PATH"
  export PATH="$HOME/.rbenv/bin:$PATH"
  eval "$(rbenv init -)"
fi

export GEM_HOME="$HOME/.local"

# kubectl
if _command kubectl; then
  source <(kubectl completion zsh)
fi

if [ -d "$HOME/src" ]; then
  CDPATH=".:$(find ~/src -mindepth 2 -maxdepth 2 -type d -printf "%p:" | sed 's/:$//g')"
  export CDPATH
fi

if _command dircolors; then
  eval "$(dircolors "$HOME/.dir_colors")"
fi
alias ls="ls -lFAh --group-directories-first --color=always"

if [ -f "/usr/local/bin/aws_zsh_completer.sh" ]; then
  source "/usr/local/bin/aws_zsh_completer.sh"
fi

export PATH="$PATH:$HOME/bin"
export LESSCHARSET=utf-8

# GOROOT-based install location
if _command go; then
  export PATH=$PATH:/usr/local/opt/go/libexec/bin
  PATH="$PATH:$(go env GOPATH)/bin"
  export PATH
fi

# Rust
# shellcheck source=./.cargo/env
if [ -f "$HOME/.cargo/env" ]; then source "$HOME/.cargo/env"; fi

# Keychain
if _command keychain; then eval "$(keychain --eval --quiet --inherit any)"; fi

# Homebrew curl
if [ -f /usr/local/opt/curl/bin/curl ]; then export PATH="/usr/local/opt/curl/bin:$PATH"; fi

# https://unix.stackexchange.com/a/377765
# known hosts completion
zstyle -e ':completion:*:(ssh|scp|sftp|rsh|rsync):hosts' hosts 'reply=(${=${${(f)"$(cat {/etc/ssh_,~/.ssh/known_}hosts(|2)(N) /dev/null)"}%%[# ]*}//,/ })'

# https://github.com/zsh-users/zsh-autosuggestions
export ZSH_AUTOSUGGEST_USE_ASYNC=true
source "/usr/local/share/zsh-autosuggestions/zsh-autosuggestions.zsh" 2>/dev/null || true
bindkey '^ ' autosuggest-acceptx

# What do I look like, a guy who's not lazy?
if command -v kubectl >/dev/null; then
  alias k=kubectl
  alias kd='kubectl describe'
  alias kdp='kubectl describe pod'
  alias kg='kubectl get'
  alias kgp='kubectl get pod'
  alias ke='kubectl exec -it'
fi

if command -v kubectx >/dev/null; then alias kctx=kubectx; fi
if command -v kubens >/dev/null; then alias kns=kubens; fi

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

if command -v pyenv 1>/dev/null 2>&1; then
  eval "$(pyenv init -)"
fi

if command -v saml2aws 1>/dev/null 2>&1; then
  eval "$(saml2aws --completion-script-zsh)"
fi

[ -f ~/.fzf.zsh ] && source ~/.fzf.zsh

source "/usr/local/opt/asdf/libexec/asdf.sh" 2>/dev/null || true

# https://github.com/zsh-users/zsh-syntax-highlighting
# Keep this last! https://github.com/zsh-users/zsh-syntax-highlighting#why-must-zsh-syntax-highlightingzsh-be-sourced-at-the-end-of-the-zshrc-file
source "/usr/local/share/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh" 2>/dev/null || true
export PATH="/usr/local/opt/openssl@1.1/bin:$PATH"
