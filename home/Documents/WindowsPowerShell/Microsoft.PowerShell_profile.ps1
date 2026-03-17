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
