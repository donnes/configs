# If you come from bash you might have to change your $PATH.
# export PATH=$HOME/bin:$HOME/.local/bin:/usr/local/bin:$PATH
export PATH="$HOME/.local/bin:$PATH"

# Path to your Oh My Zsh installation.
export ZSH="$HOME/.oh-my-zsh"

# Theme
ZSH_THEME="robbyrussell"

# Plugins
plugins=(git)

source $ZSH/oh-my-zsh.sh

# User configuration

# Aliases
alias cdc="z ~/.syncode/repo"
alias lg="lazygit"
alias ocgac='git add -A && git commit -m "$(opencode run "Write a concise commit message (max 80 characters) based on the staged changes. Only output the commit message, nothing else." 2>&1)"'
alias ocgcm='opencode run "Write a concise commit message (max 80 characters) based on the staged changes. Only output the commit message, nothing else." 2>&1'
alias nv="nvim"
alias oc="opencode"
alias c="cursor"
alias ws="windsurf"
alias cc="claude --dangerously-skip-permissions"

# Language
export LANG=en_US.UTF-8

# fnm
eval "$(fnm env --use-on-cd)"

# Zoxide
eval "$(zoxide init zsh)"

# fnm
FNM_PATH="$HOME/Library/Application Support/fnm"
if [ -d "$FNM_PATH" ]; then
  export PATH="$HOME/Library/Application Support/fnm:$PATH"
  eval "`fnm env`"
fi

# bun completions
[ -s "$HOME/.bun/_bun" ] && source "$HOME/.bun/_bun"

# bun
export BUN_INSTALL="$HOME/.bun"
export PATH="$BUN_INSTALL/bin:$PATH"

# Atuin
export ATUIN_INSTALL="$HOME/.atuin"
export PATH="$ATUIN_INSTALL/bin:$PATH"
eval "$(atuin init zsh)"

# Ruby
eval "$(rbenv init -)"

# Android SDK & Java SDK
export ANDROID_SDK_ROOT="$HOME/Library/Android/sdk"
export PATH="${PATH}:$HOME/Library/Android/sdk/platform-tools"
export JAVA_HOME=/Library/Java/JavaVirtualMachines/zulu-17.jdk/Contents/Home

# Node
export NODE_OPTIONS=--max-old-space-size=4096
export NODE_BINARY=$(which node)

# pnpm
export PNPM_HOME="$HOME/Library/pnpm"
case ":$PATH:" in
  *":$PNPM_HOME:"*) ;;
  *) export PATH="$PNPM_HOME:$PATH" ;;
esac

# Eza
alias ls="eza --color=auto --long --git --no-filesize --icons=always --no-time --no-user --no-permissions"

# Windsurf
export PATH="$HOME/.codeium/windsurf/bin:$PATH"
export EDITOR="c --wait"

# bob
export PATH="/Users/$USER/.local/share/bob/nvim-bin/:$PATH"

# opencode
export PATH="$HOME/.opencode/bin:$PATH"
alias ocs-start="launchctl load ~/Library/LaunchAgents/com.opencode.server.plist"
alias ocs-stop="launchctl unload ~/Library/LaunchAgents/com.opencode.server.plist"
alias ocs-restart="launchctl unload ~/Library/LaunchAgents/com.opencode.server.plist && launchctl load ~/Library/LaunchAgents/com.opencode.server.plist"
alias ocs-status="launchctl list | grep opencode"
alias ocs-logs="tail -f /tmp/opencode.log /tmp/opencode.error.log"

# tailscale
alias tailscale="/Applications/Tailscale.app/Contents/MacOS/Tailscale"

# opencode
export PATH=/Users/donaldsilveira/.opencode/bin:$PATH
