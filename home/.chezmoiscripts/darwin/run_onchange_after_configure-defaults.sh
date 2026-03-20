#!/bin/bash

set -eufo pipefail

# Keyboard
defaults write -g InitialKeyRepeat -int 15
defaults write -g KeyRepeat -int 2
# Disable press-and-hold for keys in favor of key repeat
defaults write -g ApplePressAndHoldEnabled -bool false
# Use F1, F2, etc. keys as standard function keys
defaults write -g com.apple.keyboard.fnState -bool true
# Enable natural scrolling so trackpad feels right
# Use https://pilotmoon.com/scrollreverser to keep mouse settings right
defaults write -g com.apple.swipescrolldirection -int 0
# Enable full keyboard access for all controls (e.g. enable Tab in modal dialogs)
defaults write -g AppleKeyboardUIMode -int 2
# Disable auto everything
defaults write -g NSAutomaticCapitalizationEnabled -int 0
defaults write -g NSAutomaticDashSubstitutionEnabled -int 0
defaults write -g NSAutomaticInlinePredictionEnabled -int 0
defaults write -g NSAutomaticPeriodSubstitutionEnabled -int 0
defaults write -g NSAutomaticQuoteSubstitutionEnabled -int 0
defaults write -g NSAutomaticSpellingCorrectionEnabled -int 0
defaults write -g NSAutomaticTextCorrectionEnabled -int 0
defaults write -g NSAutomaticWindowAnimationsEnabled -int 0
defaults write -g NSUserDictionaryReplacementItems '()'
defaults write -g WebAutomaticSpellingCorrectionEnabled -int 0
# Enable ctrl + cmd dragging of windows from anywhere in the window, not just the title bar
defaults write -g NSWindowShouldDragOnGesture -bool true

# Finder
defaults write -g AppleShowAllExtensions -bool true
defaults write -g AppleShowAllFiles -bool true
defaults write com.apple.finder ShowPathbar -bool true
# List view by default
defaults write com.apple.finder FXPreferredViewStyle -string Nlsv
defaults write com.apple.finder _FXSortFoldersFirst -bool true
# Search the current folder by default when performing a search in Finder
defaults write com.apple.finder FXDefaultSearchScope -string SCcf
# Don't show the warning when changing a file extension
defaults write com.apple.finder FXEnableExtensionChangeWarning -bool false
# Save to disk (not iCloud) by default
defaults write NSGlobalDomain NSDocumentSaveNewDocumentsToCloud -bool false

# Dock
defaults write com.apple.dock orientation -string bottom
defaults write com.apple.dock static-only -bool true
defaults write com.apple.dock show-process-indicators -bool false
defaults write com.apple.dock contents-immutable -bool true
defaults write com.apple.dock size-immutable -bool true
defaults write com.apple.dock position-immutable -bool true
defaults write com.apple.dock show-recents -bool false
defaults write com.apple.dock tilesize -int 64
defaults write com.apple.dock autohide -bool true
defaults write com.apple.dock autohide-delay -float 0
defaults write com.apple.dock autohide-time-modifier -float 0

killall Dock
killall Finder
killall SystemUIServer
