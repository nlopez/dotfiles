#!/bin/bash

set -eufo pipefail

# Keyboard
defaults write -g InitialKeyRepeat -int 15
defaults write -g KeyRepeat -int 2
# Disable press-and-hold for keys in favor of key repeat
defaults write -g ApplePressAndHoldEnabled -bool false
# Use F1, F2, etc. keys as standard function keys
defaults write -g com.apple.keyboard.fnState -bool true
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

# Trackpad
# Unnatural scrolling
defaults write -g com.apple.swipescrolldirection -bool false
defaults write -g com.apple.trackpad.forceClick -int 0
# Disable smooth scrolling
defaults write -g NSScrollAnimationEnabled -bool false

# Finder
defaults write -g AppleShowAllExtensions -bool true
defaults write -g AppleShowAllFiles -bool true
defaults write com.apple.finder ShowPathbar -bool true

# Default to details list view in Finder
defaults write com.apple.finder FXPreferredViewStyle -string "Nlsv"

# Sort folders first
defaults write com.apple.finder _FXSortFoldersFirst -bool true

# Search the current folder by default when performing a search in Finder
defaults write com.apple.finder FXDefaultSearchScope -string "SCcf"

# Don't show the warning when changing a file extension
defaults write com.apple.finder FXEnableExtensionChangeWarning -bool false

# Prefer local disk over iCloud
defaults write NSGlobalDomain NSDocumentSaveNewDocumentsToCloud -bool false

# Avoid creating .DS_Store files on network or USB volumes
defaults write com.apple.desktopservices DSDontWriteNetworkStores -bool true
defaults write com.apple.desktopservices DSDontWriteUSBStores -bool true

# Expand the following File Info panes by default:
# "General", "Open with", and "Sharing & Permissions"
defaults write com.apple.finder FXInfoPanesExpanded -dict \
	General -bool true \
	OpenWith -bool true \
  Preview -bool true \
	Privileges -bool true

# Hide widgets on the desktop
defaults write com.apple.WindowManager HideDesktop -int 1

# Trackpad window management gestures
defaults write com.apple.dock showDesktopGestureEnabled -bool false
defaults write com.apple.dock showLaunchpadGestureEnabled -bool true
defaults write com.apple.dock showMissionControlGestureEnabled -bool true

# Reduce menu bar item spacing
defaults write -g NSStatusItemSpacing -int 6
defaults write -g NSStatusItemSelectionPadding -int 6

# Dock
defaults write com.apple.dock orientation -string "bottom"
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
defaults write com.apple.dock mineffect -string "scale"
# Window title bar double-click action: No Action
defaults write -g AppleActionOnDoubleClick -string "None"

# Misc
# Enable ctrl + cmd dragging of windows from anywhere in the window, not just the title bar
defaults write -g NSWindowShouldDragOnGesture -bool true
defaults write com.apple.Accessibility ReduceMotionEnabled -int 1

# Spaces
# Enable "Displays have separate Spaces"
defaults write com.apple.spaces spans-displays -bool false
# Disable most recently used Spaces rearrangement
defaults write com.apple.dock mru-spaces -bool false
# Don't group windows by app
defaults write com.apple.dock expose-group-apps -bool false
# Don't switch to Space on application activate
defaults write -g AppleSpacesSwitchOnActivate -bool false
# Don't enter MC via dragging
defaults write com.apple.dock enterMissionControlByTopWindowDrag -bool false

# Stage Manager
defaults write com.apple.WindowManager GloballyEnabled -bool false

# Disable Hot Corners
defaults write com.apple.dock wvous-tl-corner -int 1
defaults write com.apple.dock wvous-bl-corner -int 1
defaults write com.apple.dock wvous-tr-corner -int 1
defaults write com.apple.dock wvous-br-corner -int 1

killall Dock
killall Finder
killall SystemUIServer
