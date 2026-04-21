#Requires -RunAsAdministrator
# Disable built-in auto-updaters for Chromium-based browsers managed via Scoop.
# Google Update: https://support.google.com/chrome/a/answer/6350036
# Brave: https://github.com/brave/brave-browser/issues/5576

$policies = @(
     # Google Update (Chrome) — https://support.google.com/chrome/a/answer/6350036
     @{ Path = 'HKLM:\SOFTWARE\Policies\Google\Update'; Name = 'AutoUpdateCheckPeriodMinutes'; Value = 0 }
     @{ Path = 'HKLM:\SOFTWARE\Policies\Google\Update'; Name = 'UpdateDefault';                Value = 0 }
     # Brave — https://github.com/brave/brave-browser/issues/5576
     @{ Path = 'HKLM:\SOFTWARE\WOW6432Node\BraveSoftware\UpdateDev'; Name = 'LastCheckPeriodSec'; Value = 0 }
     @{ Path = 'HKLM:\SOFTWARE\BraveSoftware\UpdateDev';             Name = 'LastCheckPeriodSec'; Value = 0 }
)

foreach ($policy in $policies) {
     if (-not (Test-Path $policy.Path)) {
          New-Item -Path $policy.Path -Force | Out-Null
     }
     Set-ItemProperty -Path $policy.Path -Name $policy.Name -Value $policy.Value -Type DWord
}
