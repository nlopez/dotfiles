$env:Path += ";$env:UserProfile\bin"
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
Set-Alias -Name e -Value code
Import-Module gsudoModule
