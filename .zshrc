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
# Show completion status
zstyle ":completion:*" show-completer true
zstyle ':completion:*' matcher-list '' 'm:{a-zA-Z}={A-Za-z}' 'r:|[._-]=* r:|=*' 'l:|=* r:|=*'
# if [ -f /usr/local/bin/aws_zsh_completer.sh ]; then

# fi

# correction
setopt correctall

# git
alias g=git
alias gup="git pull --rebase"
alias gst="git status"
alias gc="git commit"
alias grhh="git rest --hard HEAD"

# Sublime
export EDITOR="reattach-to-user-namespace subl --add --wait"
alias e="reattach-to-user-namespace subl --add"

# Misc
cdpath=( "$HOME/src" )
setopt autocd
setopt extendedglob

# History
export HISTSIZE=2000
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

alias ls="ls --color=always"

source "/usr/local/bin/aws_zsh_completer.sh"
