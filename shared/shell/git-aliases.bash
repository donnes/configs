# Bash-compatible equivalents of common Oh My Zsh Git plugin aliases.
# Omarchy's g, gcm, gcam, and gcad definitions intentionally win.

git_current_branch() {
  git symbolic-ref --quiet --short HEAD 2>/dev/null
}

git_main_branch() {
  local ref remote
  for ref in main trunk mainline default stable master; do
    if git show-ref --quiet --verify "refs/heads/$ref"; then
      printf '%s\n' "$ref"
      return 0
    fi
  done
  for remote in origin upstream; do
    ref="$(git symbolic-ref --quiet --short "refs/remotes/$remote/HEAD" 2>/dev/null)" || continue
    printf '%s\n' "${ref#"$remote/"}"
    return 0
  done
  printf 'master\n'
  return 1
}

alias ga='git add'
alias gaa='git add --all'
alias gapa='git add --patch'
alias gau='git add --update'
alias gav='git add --verbose'
alias gb='git branch'
alias gba='git branch --all'
alias gbd='git branch --delete'
alias gbD='git branch --delete --force'
alias gbm='git branch --move'
alias gbnm='git branch --no-merged'
alias gbr='git branch --remotes'
alias gco='git checkout'
alias gcor='git checkout --recurse-submodules'
alias gcb='git checkout -b'
alias gcB='git checkout -B'
alias gcp='git cherry-pick'
alias gcpa='git cherry-pick --abort'
alias gcpc='git cherry-pick --continue'
alias gclean='git clean --interactive -d'
alias gcl='git clone --recurse-submodules'
alias gc='git commit --verbose'
alias gca='git commit --verbose --all'
alias gcmsg='git commit --message'
alias gcn='git commit --verbose --no-edit'
alias gcf='git config --list'
alias gcfu='git commit --fixup'
alias gd='git diff'
alias gdca='git diff --cached'
alias gdcw='git diff --cached --word-diff'
alias gds='git diff --staged'
alias gdw='git diff --word-diff'
alias gf='git fetch'
alias gfa='git fetch --all --tags --prune'
alias gfo='git fetch origin'
alias gl='git pull'
alias gpr='git pull --rebase'
alias gpra='git pull --rebase --autostash'
alias gp='git push'
alias gpd='git push --dry-run'
alias gpf='git push --force-with-lease --force-if-includes'
alias gpv='git push --verbose'
alias gpoat='git push origin --all && git push origin --tags'
alias gpod='git push origin --delete'
alias glo='git log --oneline --decorate'
alias glog='git log --oneline --decorate --graph'
alias gloga='git log --oneline --decorate --graph --all'
alias glg='git log --stat'
alias glgp='git log --stat --patch'
alias gm='git merge'
alias gma='git merge --abort'
alias gmc='git merge --continue'
alias gms='git merge --squash'
alias gmff='git merge --ff-only'
alias gr='git remote'
alias gra='git remote add'
alias grrm='git remote remove'
alias grmv='git remote rename'
alias grset='git remote set-url'
alias grup='git remote update'
alias grv='git remote --verbose'
alias grb='git rebase'
alias grba='git rebase --abort'
alias grbc='git rebase --continue'
alias grbi='git rebase --interactive'
alias grbo='git rebase --onto'
alias grbs='git rebase --skip'
alias grf='git reflog'
alias grh='git reset'
alias gru='git reset --'
alias grhh='git reset --hard'
alias grhk='git reset --keep'
alias grhs='git reset --soft'
alias grs='git restore'
alias grss='git restore --source'
alias grst='git restore --staged'
alias grev='git revert'
alias greva='git revert --abort'
alias grevc='git revert --continue'
alias grm='git rm'
alias grmc='git rm --cached'
alias gsh='git show'
alias gsps='git show --pretty=short --show-signature'
alias gst='git status'
alias gss='git status --short'
alias gsb='git status --short --branch'
alias gsta='git stash push'
alias gstaa='git stash apply'
alias gstall='git stash --all'
alias gstc='git stash clear'
alias gstd='git stash drop'
alias gstl='git stash list'
alias gstp='git stash pop'
alias gsts='git stash show --patch'
alias gstu='git stash push --include-untracked'
alias gsw='git switch'
alias gswc='git switch --create'
alias gta='git tag --annotate'
alias gts='git tag --sign'
alias gtv='git tag --sort=-v:refname'
alias gwt='git worktree'
alias gwta='git worktree add'
alias gwtls='git worktree list'
alias gwtmv='git worktree move'
alias gwtrm='git worktree remove'
alias grt='cd "$(git rev-parse --show-toplevel || printf .)"'

ggl() {
  local branch="${1:-$(git_current_branch)}"
  [[ -n "$branch" ]] || return 1
  git pull origin "$branch"
}

ggp() {
  local branch="${1:-$(git_current_branch)}"
  [[ -n "$branch" ]] || return 1
  git push origin "$branch"
}

ggu() {
  local branch="${1:-$(git_current_branch)}"
  [[ -n "$branch" ]] || return 1
  git pull --rebase origin "$branch"
}

ggpnp() {
  ggl "$@" && ggp "$@"
}

gpsup() {
  local branch
  branch="$(git_current_branch)" || return 1
  git push --set-upstream origin "$branch"
}

ggpush() {
  ggp "$@"
}

ggpull() {
  ggl "$@"
}
