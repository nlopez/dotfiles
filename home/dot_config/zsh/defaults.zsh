# Shell defaults: options, completion styles, key bindings, aliases.
#
# Replaces the pieces of Oh My Zsh's lib/*.zsh this setup relied on. Not ported
# because they were already off or unused: history.zsh and grep.zsh (blanked by
# custom/lib overrides; atuin owns history), correction (opt-in), terminal-title
# hooks (DISABLE_AUTO_TITLE), git prompt helpers, and the take/open_command/
# clipcopy helpers.
#
# Sourced from .zshrc before compinit, so everything here is plain zsh setup.

autoload -Uz add-zsh-hook add-zle-hook-widget is-at-least
autoload -U colors && colors
zmodload -i zsh/complist
zmodload zsh/terminfo

###############################################################################
# Options
###############################################################################
setopt prompt_subst         # pure and the AWS-profile prompt segment rely on it
setopt auto_cd auto_pushd pushd_ignore_dups pushdminus
setopt multios              # redirect to multiple streams: echo >f1 >f2
setopt long_list_jobs
setopt interactivecomments
setopt auto_menu complete_in_word always_to_end
unsetopt menu_complete      # don't autoselect the first completion entry
unsetopt flowcontrol        # free up ^S / ^Q

# OMZ lib/completion.zsh: treat every punctuation char (/ - _ . = etc.) as a
# word boundary, so Ctrl-W / Alt-B / Ctrl-Left stop at path segments.
WORDCHARS=''

###############################################################################
# Completion styles (compinit itself runs in .zshrc)
###############################################################################
zstyle ':completion:*:*:*:*:*' menu select
# Case-insensitive, then partial-word matching.
zstyle ':completion:*' matcher-list 'm:{[:lower:][:upper:]}={[:upper:][:lower:]}' 'r:|=*' 'l:|=* r:|=*'
zstyle ':completion:*' special-dirs true           # complete . and ..
zstyle ':completion:*' list-colors ''
zstyle ':completion:*:*:kill:*:processes' list-colors '=(#b) #([0-9]#) ([0-9a-z-]#)*=01;34=0=01'
zstyle ':completion:*:*:*:*:processes' command "ps -u $USERNAME -o pid,user,comm -w -w"
zstyle ':completion:*:cd:*' tag-order local-directories directory-stack path-directories
zstyle ':completion:*' use-cache yes
zstyle ':completion:*' cache-path "${XDG_CACHE_HOME:-$HOME/.cache}/zsh/zcompcache"
zstyle ':completion:*:*:*:users' ignored-patterns \
  adm amanda apache at avahi avahi-autoipd beaglidx bin cacti canna \
  clamav daemon dbus distcache dovecot fax ftp games gdm gkrellmd \
  gopher hacluster haldaemon halt hsqldb ident junkbust ldap lp mail \
  mailman mailnull mldonkey mysql nagios named netdump news nfsnobody \
  nobody nscd ntp nut nx obsrvd openvpn operator pcap papaya postfix \
  postgres privoxy pulse pvm quagga radvd rpc rpcuser rpm shutdown \
  squid sshd sync uucp vcsa xfs '_*'
zstyle '*' single-ignored show
bindkey -M menuselect '^o' accept-and-infer-next-history

# Some tools (terraform, aws, ...) register completions via `complete -C`.
autoload -U +X bashcompinit && bashcompinit

###############################################################################
# Key bindings
###############################################################################
bindkey -e

# $terminfo values are only valid while the terminal is in application mode.
if (( ${+terminfo[smkx]} && ${+terminfo[rmkx]} )); then
  function zle-line-init()   { echoti smkx }
  function zle-line-finish() { echoti rmkx }
  zle -N zle-line-init
  zle -N zle-line-finish
fi

# Bind in every keymap: _bind <key> <widget>
function _bind() { local m; for m in emacs viins vicmd; do bindkey -M $m "$1" "$2"; done }

autoload -U up-line-or-beginning-search down-line-or-beginning-search
zle -N up-line-or-beginning-search
zle -N down-line-or-beginning-search
_bind '^[[A' up-line-or-beginning-search
_bind '^[[B' down-line-or-beginning-search
[[ -n "${terminfo[kcuu1]}" ]] && _bind "${terminfo[kcuu1]}" up-line-or-beginning-search
[[ -n "${terminfo[kcud1]}" ]] && _bind "${terminfo[kcud1]}" down-line-or-beginning-search
[[ -n "${terminfo[kpp]}"   ]] && _bind "${terminfo[kpp]}"   up-line-or-history
[[ -n "${terminfo[knp]}"   ]] && _bind "${terminfo[knp]}"   down-line-or-history
[[ -n "${terminfo[kcbt]}"  ]] && _bind "${terminfo[kcbt]}"  reverse-menu-complete  # Shift-Tab
_bind '^?' backward-delete-char                                                   # Backspace
if [[ -n "${terminfo[kdch1]}" ]]; then
  _bind "${terminfo[kdch1]}" delete-char                                          # Delete
else
  _bind '^[[3~'  delete-char
  _bind '^[3;5~' delete-char
fi
_bind '^[[3;5~' kill-word        # Ctrl-Delete
_bind '^[[1;5C' forward-word     # Ctrl-Right
_bind '^[[1;5D' backward-word    # Ctrl-Left
unfunction _bind

bindkey '\ew' kill-region
bindkey ' ' magic-space          # no history expansion on space (zabrze rebinds later)
bindkey '^[m' copy-prev-shell-word

# Quote URLs/special chars as they're typed (paste bypasses this; see .zshrc).
autoload -Uz url-quote-magic
zle -N self-insert url-quote-magic

###############################################################################
# Environment, aliases
###############################################################################
(( ${+commands[less]} )) && { : ${PAGER:=less}; : ${LESS:=-R}; export PAGER LESS }

export LSCOLORS="Gxfxcxdxbxegedabagacad"   # BSD ls
if [[ -z "$LS_COLORS" ]]; then              # GNU ls
  if (( $+commands[dircolors] )); then
    source <(dircolors -b)
  else
    export LS_COLORS="di=1;36:ln=35:so=32:pi=33:ex=31:bd=34;46:cd=34;43:su=30;41:sg=30;46:tw=30;42:ow=30;43"
  fi
fi
# GNU coreutils (Nix) first on PATH; fall back to BSD ls.
if command ls --color=auto /dev/null &>/dev/null; then
  alias ls='ls --color=auto'
else
  alias ls='ls -G'
fi
function diff { command diff --color "$@" }

alias -- -='cd -'
