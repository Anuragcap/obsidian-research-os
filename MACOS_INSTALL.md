
## Prerequisites

```bash
bash --version          # Should be 5.0+ (macOS has 3.2 by default)
python3 --version       # Should be 3.10+
git --version
ls /Applications/Obsidian.app

heredoc> ## Install Bash
heredoc> 
heredoc> ```bash
heredoc> brew install bash
heredoc> echo 'export PATH="/usr/local/bin:$PATH"' >> ~/.zshrc
heredoc> source ~/.zshrc
heredoc> ```
heredoc> 
heredoc> ## Install Obsidian
heredoc> 
heredoc> ```bash
heredoc> brew install obsidian
heredoc> open -a Obsidian
heredoc> ```
heredoc> 
heredoc> Then in Obsidian: Settings → General → toggle "Command line interface" ON
heredoc> 
heredoc> ## Install obs
heredoc> 
heredoc> ```bash
heredoc> chmod +x bin/obs
heredoc> mkdir -p "$HOME/.local/bin"
heredoc> ln -sf "$(pwd)/bin/obs" "$HOME/.local/bin/obs"
heredoc> echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
heredoc> source ~/.zshrc
heredoc> obs help
heredoc> ```
heredoc> 
heredoc> ## Test
heredoc> 
heredoc> ```bash
heredoc> obs setup ~/Documents/test-obs-vault
heredoc> obs init
heredoc> obs doctor
heredoc> ```
heredoc> 
heredoc> Expected: All ✓
heredoc> EOF







