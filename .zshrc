export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

# Enable Ctrl-x-e to edit command line
autoload -U edit-command-line
zle -N edit-command-line
bindkey '^xe' edit-command-line
bindkey '^x^e' edit-command-line

fpath=(
  "$HOME/.zfunctions"
  /usr/local/share/zsh/site-functions
  $fpath
)

# Prompt
autoload -Uz promptinit
promptinit
prompt pure
PROMPT='%(?.%F{green}.%F{red})❯%f '

# Completion
autoload -Uz compinit
compinit

# Show completion status
# # http://stackoverflow.com/a/844299
expand-or-complete-with-dots() {
  echo -n "\e[31m...\e[0m"
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
alias gst="git status"
alias gc="git commit"
alias grhh="git reset --hard HEAD"
alias gp="git push"

# Sublime
export EDITOR="reattach-to-user-namespace subl --add --wait"
alias e="reattach-to-user-namespace subl --add"

# Misc
cdpath=( "$HOME/src" )
setopt autocd
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

# direnv
if which direnv >/dev/null 2>&1; then eval "$(direnv hook zsh)"; fi
# pipenv
if which pipenv >/dev/null 2>&1; then eval "$(env _PIPENV_COMPLETE=source-zsh pipenv)"; fi
# kubectl
if which kubectl >/dev/null 2>&1; then eval "$(kubectl completion zsh)"; fi
# rbenv
if which rbenv >/dev/null 2>&1; then
  export PATH="$HOME/.rbenv/plugins/ruby-build/bin:$PATH"
  export PATH="$HOME/.rbenv/bin:$PATH"
  eval "$(rbenv init -)"
fi

# use gnu utils with regular names
if which greadlink >/dev/null 2>&1; then
  export PATH="/usr/local/opt/coreutils/libexec/gnubin:$PATH"
  export MANPATH="/usr/local/opt/coreutils/libexec/gnuman:$MANPATH"
fi
if which gsed >/dev/null 2>&1; then
  export PATH="/usr/local/opt/gnu-sed/libexec/gnubin:$PATH"
  export MANPATH="/usr/local/opt/gnu-sed/libexec/gnuman:$MANPATH"
fi
if which gfind >/dev/null 2>&1; then
  export PATH="/usr/local/opt/findutils/libexec/gnubin:$PATH"
  export MANPATH="/usr/local/opt/findutils/libexec/gnuman:$MANPATH"
fi
if which gtar >/dev/null 2>&1; then
  export PATH="/usr/local/opt/gnu-tar/libexec/gnubin:$PATH"
  export MANPATH="/usr/local/opt/gnu-tar/libexec/gnuman:$MANPATH"
fi

alias ls="ls -lFAh --group-directories-first --color=always"

if [ -f "/usr/local/bin/aws_zsh_completer.sh" ]; then
  source "/usr/local/bin/aws_zsh_completer.sh"
fi

export PATH="$PATH:$HOME/bin"
export LESSCHARSET=utf-8

# GOROOT-based install location
export PATH=$PATH:/usr/local/opt/go/libexec/bin
export PATH="$PATH:$(go env GOPATH)/bin"

# https://github.com/kennethreitz/pipenv/issues/184
export PIPENV_SHELL_COMPAT=1

# Homebrew python
export PATH="/usr/local/opt/python/libexec/bin:$PATH"
# pipsi
export PATH=/Users/nicklopez/.local/bin:$PATH

# https://github.com/zsh-users/zsh-syntax-highlighting
# Keep this last!
source "/usr/local/share/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh" 2>/dev/null || true
