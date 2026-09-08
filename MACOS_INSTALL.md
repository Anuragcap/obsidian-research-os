# macOS Installation Guide

## Prerequisites

bash --version
python3 --version
git --version
ls /Applications/Obsidian.app

## Install Bash

brew install bash
echo 'export PATH="/usr/local/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc

## Install Obsidian

brew install obsidian
open -a Obsidian

Then in Obsidian: Settings → General → toggle "Command line interface" ON

## Install obs

chmod +x bin/obs
mkdir -p "$HOME/.local/bin"
ln -sf "$(pwd)/bin/obs" "$HOME/.local/bin/obs"
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
obs help

## Test

obs setup ~/Documents/test-obs-vault
obs init
obs doctor

Expected: All ✓
