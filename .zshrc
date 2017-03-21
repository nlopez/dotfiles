source ~/.antigen/antigen.zsh
antigen use oh-my-zsh
antigen bundles <<EOBUNDLES
  mafredri/zsh-async
  sindresorhus/pure
  zsh-users/zsh-completions
  zsh-users/zsh-syntax-highlighting
  zsh_reload
  gitfast
  colored-man-pages
  aws
  kubectl
  mosh
  nmap
  pip
  terraform
  virtualenv
  vault
EOBUNDLES
antigen apply

alias e='subl --add'
export EDITOR='subl --add --wait'

cdpath=(.. ~ ~/src)
export PATH="$HOME/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

# direnv
if which direnv >/dev/null 2>&1; then eval "$(direnv hook zsh)"; fi

# pipenv
if which pipenv >/dev/null 2>&1; then eval "$(env _PIPENV_COMPLETE=source-zsh pipenv)"; fi

if [[ -f /usr/local/share/chtf/chtf.sh ]]; then
  source "/usr/local/share/chtf/chtf.sh"
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
