# Bash integration for Obsidian Research OS.
#
# Source this file from ~/.bashrc after installing `obs`:
#   source "$HOME/Documents/obsidian-research-os/shell/obs.bash"
#
# Bash expands history references (such as `!!`) before it invokes a command,
# even when they appear inside double quotes. Disable that expansion so task
# text like `obs task add "Follow up!!!"` reaches `obs` unchanged.
set +o histexpand
