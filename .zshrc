source ~/.antigen/antigen.zsh
antigen use oh-my-zsh
antigen bundles <<EOBUNDLES
  terraform
  aws
  colored-man-pages
  gitfast
  kubectl
  mafredri/zsh-async
  mosh
  nmap
  pip
  sindresorhus/pure
  terraform
  virtualenv
  zsh-users/zsh-completions
  zsh-users/zsh-syntax-highlighting
  zsh_reload
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
