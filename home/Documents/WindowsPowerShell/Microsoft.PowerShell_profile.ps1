$env:Path += ";$env:UserProfile\bin"
Set-Alias -Name g -Value git
Import-Module gsudoModule
Invoke-Expression (& tirith init)
