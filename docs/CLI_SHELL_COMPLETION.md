# X-Agent CLI Shell Completion

Shell completion for X-Agent CLI provides tab-completion for commands, options, and arguments across multiple shells.

## Supported Shells

- **Bash** (Linux, macOS, WSL)
- **Zsh** (macOS default, Linux)
- **Fish** (Linux, macOS)
- **PowerShell** (Windows)

## Quick Install

### Automatic Installation (Recommended)

The easiest way to install shell completion:

```bash
# For Bash
xagent completion bash --install

# For Zsh
xagent completion zsh --install

# For Fish
xagent completion fish --install
```

After installation, restart your terminal or source your shell configuration:

```bash
# Bash
source ~/.bashrc

# Zsh
source ~/.zshrc

# Fish (automatic, no action needed)
```

### Manual Installation

If automatic installation doesn't work, use manual installation:

#### Bash

1. **Generate completion script:**
   ```bash
   xagent --show-completion bash > ~/.bash_completion.d/xagent
   ```

2. **Add to ~/.bashrc:**
   ```bash
   echo 'source ~/.bash_completion.d/xagent' >> ~/.bashrc
   ```

3. **Reload:**
   ```bash
   source ~/.bashrc
   ```

#### Zsh

1. **Create completion directory:**
   ```bash
   mkdir -p ~/.zsh/completion
   ```

2. **Generate completion script:**
   ```bash
   xagent --show-completion zsh > ~/.zsh/completion/_xagent
   ```

3. **Add to ~/.zshrc:**
   ```bash
   echo 'fpath=(~/.zsh/completion $fpath)' >> ~/.zshrc
   echo 'autoload -Uz compinit && compinit' >> ~/.zshrc
   ```

4. **Reload:**
   ```bash
   source ~/.zshrc
   ```

#### Fish

1. **Generate completion script:**
   ```bash
   xagent --show-completion fish > ~/.config/fish/completions/xagent.fish
   ```

   Fish will automatically load completions on next shell start.

#### PowerShell

1. **Generate completion script:**
   ```powershell
   xagent --show-completion powershell > xagent_completion.ps1
   ```

2. **Add to PowerShell profile:**
   ```powershell
   echo '. C:\path\to\xagent_completion.ps1' >> $PROFILE
   ```

3. **Reload:**
   ```powershell
   . $PROFILE
   ```

## Usage

Once installed, tab completion will work for:

### Commands

Press TAB after `xagent` to see available commands:

```bash
xagent [TAB]
# Shows: interactive, start, status, version, completion
```

### Options

Press TAB after `--` to see available options:

```bash
xagent start --[TAB]
# Shows: --goal, --mode, --help
```

### Arguments

Press TAB to complete argument values where applicable:

```bash
xagent completion [TAB]
# Shows: bash, zsh, fish, powershell
```

## Completion Features

### Command Completion

All main commands are completed:
- `interactive` - Start interactive mode
- `start` - Start agent with goal
- `status` - Show agent status
- `version` - Show version information
- `completion` - Manage shell completion

### Option Completion

All command options are completed:
- `--goal` - Goal description
- `--mode` - Agent mode (autonomous, focus, idle, emergency)
- `--help` - Show help message
- `--install` - Install completion (for completion command)
- `--show` - Show instructions (for completion command)

### Argument Completion

Shell types for completion command:
- `bash`
- `zsh`
- `fish`
- `powershell`

## Troubleshooting

### Completion Not Working

1. **Verify installation:**
   ```bash
   # Check if completion file exists
   ls ~/.bash_completion.d/xagent  # Bash
   ls ~/.zsh/completion/_xagent     # Zsh
   ls ~/.config/fish/completions/xagent.fish  # Fish
   ```

2. **Check shell configuration:**
   ```bash
   # Verify source line exists
   grep "xagent" ~/.bashrc  # Bash
   grep "xagent" ~/.zshrc   # Zsh
   ```

3. **Restart terminal:**
   Close and reopen your terminal window.

4. **Regenerate completion:**
   ```bash
   xagent completion bash --install  # Force reinstall
   ```

### Permission Issues

If you get permission errors during installation:

```bash
# Make sure directories exist and are writable
mkdir -p ~/.bash_completion.d
chmod 755 ~/.bash_completion.d
```

### Old Completion Script

If completion behaves strangely after updating:

```bash
# Remove old completion
rm ~/.bash_completion.d/xagent  # Bash
rm ~/.zsh/completion/_xagent     # Zsh
rm ~/.config/fish/completions/xagent.fish  # Fish

# Reinstall
xagent completion bash --install  # Your shell
```

### Zsh Compinit Warnings

If you see compinit warnings in Zsh:

```bash
# Fix insecure directories
compaudit | xargs chmod g-w
```

### Multiple Python Environments

If you use virtualenv/conda and completion stops working:

```bash
# Reinstall completion in each environment
conda activate myenv
xagent completion bash --install
```

## Advanced Configuration

### Bash Completion Directory

By default, completions are installed to `~/.bash_completion.d/`. To use a different directory:

```bash
# Custom directory
mkdir -p ~/my-completions
xagent --show-completion bash > ~/my-completions/xagent

# Add to ~/.bashrc
echo 'source ~/my-completions/xagent' >> ~/.bashrc
```

### Zsh Completion Directory

For system-wide Zsh completion:

```bash
# Install to system directory (requires sudo)
sudo xagent --show-completion zsh > /usr/local/share/zsh/site-functions/_xagent
```

### Fish Completion System-Wide

For all users on the system:

```bash
# Install to system directory (requires sudo)
sudo xagent --show-completion fish > /usr/share/fish/vendor_completions.d/xagent.fish
```

## Completion Command Reference

### Show Instructions

Display installation instructions without installing:

```bash
xagent completion bash        # Show bash instructions
xagent completion zsh         # Show zsh instructions
xagent completion fish        # Show fish instructions
xagent completion powershell  # Show powershell instructions
```

### Install Completion

Automatically install completion:

```bash
xagent completion bash --install        # Install for bash
xagent completion zsh --install         # Install for zsh
xagent completion fish --install        # Install for fish
```

### Generate Completion Script

Generate raw completion script:

```bash
xagent --show-completion bash        # Bash script
xagent --show-completion zsh         # Zsh script
xagent --show-completion fish        # Fish script
xagent --show-completion powershell  # PowerShell script
```

## Integration with IDEs

### VS Code

VS Code terminal inherits shell completion automatically.

### PyCharm

PyCharm terminal inherits shell completion automatically.

### Vim/Neovim

Terminal emulators in Vim/Neovim support completion if the shell is configured correctly.

## Uninstallation

To remove shell completion:

### Bash

```bash
rm ~/.bash_completion.d/xagent
# Remove source line from ~/.bashrc manually
```

### Zsh

```bash
rm ~/.zsh/completion/_xagent
# Remove fpath line from ~/.zshrc manually
```

### Fish

```bash
rm ~/.config/fish/completions/xagent.fish
```

### PowerShell

```powershell
Remove-Item xagent_completion.ps1
# Remove source line from $PROFILE manually
```

## Platform-Specific Notes

### macOS

On macOS, bash completion requires `bash-completion` package:

```bash
brew install bash-completion
```

Add to `~/.bash_profile`:

```bash
[[ -r "/usr/local/etc/profile.d/bash_completion.sh" ]] && . "/usr/local/etc/profile.d/bash_completion.sh"
```

### Linux

Most Linux distributions include bash completion by default.

### Windows (WSL)

WSL supports bash and zsh completion just like native Linux.

### Windows (Native PowerShell)

PowerShell completion works in both PowerShell 5.1 and PowerShell 7+.

## Contributing

To add new commands or options to completion:

1. Add command/option to CLI in `src/xagent/cli/main.py`
2. Typer automatically generates completion for new commands
3. Reinstall completion: `xagent completion bash --install`

## See Also

- [CLI Documentation](CLI.md) - Complete CLI reference
- [Quick Start Guide](QUICKSTART.md) - Getting started with X-Agent
- [Configuration Guide](CONFIGURATION.md) - Configuration options

## Support

For issues with shell completion:
- GitHub Issues: https://github.com/UnknownEngineOfficial/XAgent/issues
- Documentation: https://github.com/UnknownEngineOfficial/XAgent/tree/main/docs
