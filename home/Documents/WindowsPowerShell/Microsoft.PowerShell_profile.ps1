$env:PATH += ";$env:UserProfile\bin"
$env:PATH += ";$env:UserProfile\.local\bin"
$env:EDITOR = "code"
Set-Alias -Name g -Value git
# Remove default aliases so gc/gp can be used as git functions.
Remove-Item alias:gc -Force -ErrorAction SilentlyContinue
Remove-Item alias:gp -Force -ErrorAction SilentlyContinue
function gst { git status @args }
function ga { git add @args }
function gc { git commit @args }
function gp { git push @args }
function gup { git pull --rebase @args }
function gdc { git diff --cached @args }
function grhh { git reset --hard HEAD @args }
Set-Alias -Name e -Value code
Import-Module gsudoModule

# Git aliases (mirrors oh-my-zsh git plugin conventions used in zsh)
function gco  { git checkout @args }
function gcb  { git checkout -b @args }
function gb   { git branch @args }
function gba  { git branch -a @args }
function gbd  { git branch -d @args }
function gbD  { git branch -D @args }
function gd   { git diff @args }
function gds  { git diff --staged @args }
function gl   { git log --oneline --decorate @args }
function glg  { git log --oneline --decorate --graph @args }
function gf   { git fetch @args }
function gfa  { git fetch --all --prune @args }
function gpf  { git push --force-with-lease @args }
function gm   { git merge @args }
function gma  { git merge --abort @args }
function grb  { git rebase @args }
function grba { git rebase --abort @args }
function grbc { git rebase --continue @args }
function grbi { git rebase -i @args }
function gcp  { git cherry-pick @args }
function gcpa { git cherry-pick --abort @args }
function gcpc { git cherry-pick --continue @args }
function gsta { git stash push @args }
function gstp { git stash pop @args }
function gstl { git stash list @args }
function grh  { git reset HEAD @args }
function grs  { git restore @args }
function grss { git restore --staged @args }

# Emacs/readline-style key bindings for PSReadLine.
# PSReadLine's default Windows edit-mode doesn't map these, so bind them
# explicitly so they work consistently whether in a plain terminal or VS Code.
if (Get-Module -ListAvailable PSReadLine) {
  Set-PSReadLineKeyHandler -Chord Ctrl+a -Function BeginningOfLine
  Set-PSReadLineKeyHandler -Chord Ctrl+e -Function EndOfLine
  Set-PSReadLineKeyHandler -Chord Ctrl+f -Function ForwardChar
  Set-PSReadLineKeyHandler -Chord Ctrl+b -Function BackwardChar
  Set-PSReadLineKeyHandler -Chord Ctrl+k -Function KillLine
  Set-PSReadLineKeyHandler -Chord Ctrl+u -Function BackwardDeleteLine
  Set-PSReadLineKeyHandler -Chord Ctrl+w -Function BackwardKillWord
  Set-PSReadLineKeyHandler -Chord Ctrl+y -Function Yank
  Set-PSReadLineKeyHandler -Chord Ctrl+d -Function DeleteCharOrExit
  Set-PSReadLineKeyHandler -Chord Ctrl+p -Function PreviousHistory
  Set-PSReadLineKeyHandler -Chord Ctrl+n -Function NextHistory
  Set-PSReadLineKeyHandler -Chord Ctrl+r -Function ReverseSearchHistory
  Set-PSReadLineKeyHandler -Chord Ctrl+l -Function ClearScreen
}
