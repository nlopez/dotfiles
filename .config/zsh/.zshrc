if [[ -n "$ZSH_DO_PROFILING" ]]; then zmodload zsh/zprof; fi

function prepend_path() {
  path=($1 $path)
}

# uname logic cribbed from https://github.com/microsoft/WSL/issues/4071#issuecomment-1223393940
unameOut=$(uname -a)
case "${unameOut}" in
  *Microsoft*) OS="WSL";; #wls must be first since it will have Linux in the name too
  *microsoft*) OS="WSL2";;
  Linux*)      OS="Linux";;
  Darwin*)     OS="Mac";;
  CYGWIN*)     OS="Cygwin";;
  MINGW*)      OS="Windows";;
  *Msys)       OS="Windows";;
  *)           OS="UNKNOWN:${unameOut}"
esac

if [[ ${OS} == "Mac" ]] && sysctl -n machdep.cpu.brand_string | grep -q 'Apple M1'; then
    #Check if its an M1. This check should work even if the current processes is running under x86 emulation.
    OS="MacM1"
fi

alias _command="command -v $1 >/dev/null 2>&1"
# path construction - https://zsh.sourceforge.io/Guide/zshguide02.html#l24
prepend_path "${HOME}/.local/bin"
prepend_path "/Applications/Docker.app/Contents/Resources/bin"
prepend_path "${HOME}/.cargo/bin"

umask 077

if [[ "${OS}" == "WSL"* ]]; then
  mkdir -p ~/.1password
  if ! _command npiperelay.exe || ! _command socat; then
    echo "Error: npiperelay.exe and/or socat are not available. Exiting..."
  else
    # Configure ssh forwarding
      export SSH_AUTH_SOCK=$HOME/.ssh/agent.sock
      # need `ps -ww` to get non-truncated command for matching
      # use square brackets to generate a regex match for the process we want but that doesn't match the grep command running it!
      ALREADY_RUNNING=$(ps -auxww | grep -q "[n]piperelay.exe -ei -s //./pipe/openssh-ssh-agent"; echo $?)
      if [[ $ALREADY_RUNNING != "0" ]]; then
          if [[ -S $SSH_AUTH_SOCK ]]; then
              # not expecting the socket to exist as the forwarding command isn't running (http://www.tldp.org/LDP/abs/html/fto.html)
              echo "removing previous socket..."
              rm $SSH_AUTH_SOCK
          fi
          echo "Starting SSH-Agent relay..."
          # setsid to force new session to keep running
          # set socat to listen on $SSH_AUTH_SOCK and forward to npiperelay which then forwards to openssh-ssh-agent on windows
          (setsid socat UNIX-LISTEN:$SSH_AUTH_SOCK,fork EXEC:"npiperelay.exe -ei -s //./pipe/openssh-ssh-agent",nofork &) >/dev/null 2>&1
      fi
    fi
fi

if [[ "${OS}" == "Mac"* ]]; then
  # https://hynek.me/articles/apple-openssl-verification-surprises/
  export OPENSSL_X509_TEA_DISABLE=1
  BREW_PREFIX="/usr/local"
  if [[ "${OS}" == "MacM1" ]]; then
    BREW_PREFIX="/opt/homebrew"
  fi
fi

if [ -d "$BREW_PREFIX" ]; then
  prepend_path "$BREW_PREFIX/bin"
  # eval "$($BREW_PREFIX/bin/brew shellenv)"

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
  if _command gtime; then
    prepend_path "$BREW_PREFIX/opt/gnu-time/libexec/gnubin"
    export MANPATH="$BREW_PREFIX/opt/gnu-time/libexec/gnuman:$MANPATH"
  fi
fi

prepend_path "${BREW_PREFIX}/opt/curl/bin"
prepend_path "${BREW_PREFIX}/opt/openjdk/bin"

if [ -f "/home/linuxbrew/.linuxbrew/bin/brew" ]; then
  # shellcheck disable=SC1090
  eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)"
fi

alias dotfiles="git --git-dir=$HOME/.dotfiles/ --work-tree=$HOME"

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

if _command starship; then
  eval "$(starship init zsh)"
fi

###############################################################################
# Completion
###############################################################################
if [ -n "$BREW_PREFIX" ]; then
  FPATH=$BREW_PREFIX/share/zsh-completions:$BREW_PREFIX/share/zsh/site-functions:$FPATH
fi
autoload -Uz compinit bashcompinit

# Cache compinit for faster startup (recompile every 24 hours)
if [[ -n ${ZDOTDIR}/.zcompdump(#qN.mh+24) ]]; then
  compinit
else
  compinit -C
fi

bashcompinit

# Cribbed from https://github.com/ohmyzsh/ohmyzsh/blob/d157fc60c93fa59e757921b503e9594bd23b422c/lib/completion.zsh#L61-L75
COMPLETION_WAITING_DOTS="%F{yellow}...%f"
if [[ ${COMPLETION_WAITING_DOTS:-false} != false ]]; then
  expand-or-complete-with-dots() {
    # turn off line wrapping and print prompt-expanded "dot" sequence
    printf '\e[?7l%s\e[?7h' "${(%)COMPLETION_WAITING_DOTS}"
    zle expand-or-complete
    zle redisplay
  }
  zle -N expand-or-complete-with-dots
  # Set the function as the default tab completion widget
  bindkey -M emacs "^I" expand-or-complete-with-dots
  bindkey -M viins "^I" expand-or-complete-with-dots
  bindkey -M vicmd "^I" expand-or-complete-with-dots
fi

unsetopt menu_complete   # do not autoselect the first completion entry
unsetopt flowcontrol
setopt auto_menu         # show completion menu on successive tab press
setopt complete_in_word
setopt always_to_end

# Case-insensitive matching
zstyle ':completion:*' matcher-list 'r:|=*' 'l:|=* r:|=*'
# Use completion menu
zstyle ':completion:*' menu select
# Complete . and .. special directories
zstyle ':completion:*' special-dirs true
# Use caching so that commands like apt and dpkg complete are useable
zstyle ':completion:*' use-cache yes
zstyle ':completion:*' cache-path $ZSH_CACHE_DIR

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
  'g' 'git'
  'ga' 'git add'
  'gc' 'git commit'
  'gcd-gh' 'git checkout "$(gh repo view --json defaultBranchRef --jq .defaultBranchRef.name)"'
  'gcd' 'git checkout "$(git remote show origin | sed -n "s/.*HEAD branch: \(.*\)/\1/p")"'
  'gdc' 'git diff --cached'
  'gp' 'git push'
  'grhh' 'git reset --hard HEAD'
  'grc' 'git rebase --continue'
  'gst' 'git status'
  'gup' 'git pull --rebase'
  'k' 'kubectl'
  'kd' 'kubectl describe'
  'kdp' 'kubectl describe pod'
  'ke' 'kubectl exec -it'
  'kg' 'kubectl get'
  'kgp' 'kubectl get pod'
  'tfapply' 'terraform apply'
  'tfinit' 'terraform init'
  'tfplan' 'terraform plan'
  'tfshow' 'terraform show tfplan'
  'tfsl' 'terraform state list'
  'tfss' 'terraform state show'
  'tfu' 'terraform force-unlock -force'
)

# shellcheck source=./.zshrc_local
if [ -f "$ZDOTDIR/.zshrc_local" ]; then source "$ZDOTDIR/.zshrc_local"; fi

for abbr in ${(k)abbrevs}; do
   alias $abbr="${abbrevs[$abbr]}"
done

magic-abbrev-expand() {
  local MATCH
  LBUFFER=${LBUFFER%%(#m)[_a-zA-Z0-9]#}
  LBUFFER+=${abbrevs[$MATCH]:-$MATCH}

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
if _command cursor; then
  export EDITOR="cursor --add --wait"
  alias e="cursor --add"
elif _command code; then
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
setopt kshoptionprint

# History
export HISTFILE="$ZDOTDIR/.zsh_history"
export HISTSIZE=1000000000
export SAVEHIST=$HISTSIZE
setopt BANG_HIST                 # Treat the '!' character specially during expansion.
setopt EXTENDED_HISTORY          # Write the history file in the ":start:elapsed;command" format.
setopt INC_APPEND_HISTORY        # Write to the history file immediately, not when the shell exits.
setopt APPEND_HISTORY            # Always append to history, never overwrite
setopt SHARE_HISTORY             # Share history between all sessions.
setopt HIST_IGNORE_DUPS          # Don't record an entry that was just recorded again.
setopt HIST_FIND_NO_DUPS         # Do not display a line previously found.
setopt HIST_IGNORE_SPACE         # Don't record an entry starting with a space.
setopt HIST_SAVE_NO_DUPS         # Don't write duplicate entries in the history file.
setopt HIST_REDUCE_BLANKS        # Remove superfluous blanks before recording entry.
setopt HIST_VERIFY               # Don't execute immediately upon history expansion.
setopt HIST_BEEP                 # Beep when accessing nonexistent history.

# pushd
setopt autopushd pushdminus pushdsilent pushdtohome pushdignoredups
alias dh='dirs -v'
export DIRSTACKSIZE=100

# direnv
if _command direnv; then eval "$(direnv hook zsh)"; fi

if [ -d "$HOME/src" ]; then
  CDPATH=".:$(find ~/src -mindepth 2 -maxdepth 2 -type d -printf "%p:" | sed 's/:$//g')"
  export CDPATH
fi

_command dircolors && eval "$(dircolors "$HOME/.dir_colors")"
alias ls="ls -lFAh --color=auto"
# alias -g groot="$(git rev-parse --show-toplevel)"

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
if _command keychain; then eval "$(keychain --eval --quiet)"; fi

# Homebrew curl
if [ -f "${BREW_PREFIX}/opt/curl/bin/curl" ]; then prepend_path "${BREW_PREFIX}/opt/curl/bin/curl"; fi

# https://unix.stackexchange.com/a/377765
# known hosts completion
zstyle -e ':completion:*:(ssh|scp|sftp|rsh|rsync):hosts' hosts 'reply=(${=${${(f)"$(cat {/etc/ssh_,~/.ssh/known_}hosts(|2)(N) /dev/null)"}%%[# ]*}//,/ })'

if _command kubectl; then
  source <(kubectl completion zsh)
fi

_command kubectx && alias kctx=kubectx
_command kubens && alias kns=kubens
_command aws_vault && eval "$(aws-vault --completion-script-zsh)"

# serverless
# tabtab source for packages
# uninstall by removing these lines
[[ -f ~/.config/tabtab/__tabtab.zsh ]] && . ~/.config/tabtab/__tabtab.zsh || true

if [ -d  "/usr/local/Caskroom/google-cloud-sdk/latest/google-cloud-sdk" ]; then
  source /usr/local/Caskroom/google-cloud-sdk/latest/google-cloud-sdk/completion.zsh.inc
  source /usr/local/Caskroom/google-cloud-sdk/latest/google-cloud-sdk/path.zsh.inc
fi

_command saml2aws && eval "$(saml2aws --completion-script-zsh)"

# pipx autocomplete
if _command pipx; then
  _command register-python-argcomplete && eval "$(register-python-argcomplete pipx)"
  _command register-python-argcomplete3 && eval "$(register-python-argcomplete3 pipx)"
fi

[ -f ~/.fzf.zsh ] && source ~/.fzf.zsh
export FZF_TMUX=1

_command fzf && source <(fzf --zsh)

export WORDCHARS=""

source "$BREW_PREFIX/opt/asdf/libexec/asdf.sh" 2>/dev/null || true

# Try pyenv
export PYENV_ROOT="$HOME/.pyenv"
[[ -d $PYENV_ROOT/bin ]] && prepend_path "$PYENV_ROOT/bin"

_command op && eval "$(op completion zsh)"

if _command docker; then
  eval "$(docker completion zsh)"
fi

# krew
if [ -d "$HOME/.krew/bin" ] || [ -n "$KREW_ROOT" ]; then
  prepend_path "${KREW_ROOT:-$HOME/.krew}/bin"
fi

export LESS="--raw-control-chars --quit-if-one-screen"
export LESSCHARSET="utf-8"
export MANPAGER="less --use-color -Dd+r -Du+b"
# export MANROFFOPT="-P -c"
export PAGER="less"

prepend_path ~/bin

# fnm
FNM_PATH="/home/localuser/.local/share/fnm"
if [ -d "$FNM_PATH" ]; then
  export PATH="/home/localuser/.local/share/fnm:$PATH"
  eval "`fnm env`"
fi

# atuin
if [[ -f "$HOME/.atuin/bin/env" ]]; then
  . "$HOME/.atuin/bin/env"
fi
_command atuin && eval "$(atuin init zsh)"

typeset -U path

if [[ -n "$ZSH_DO_PROFILING" ]]; then zprof; fi

_command tmux && if [[ "$TMUX" == "" ]]; then tmux -u new-session -s 0 -A; fi
