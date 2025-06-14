# Trae Agent

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/) [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
 ![Alpha]( https://img.shields.io/badge/Status-Alpha-red)

**Trae Agent** is an LLM-based agent for general purpose software engineering tasks. It provides a powerful CLI interface that can understand natural language instructions and execute complex software engineering workflows using various tools and LLM providers.

*Please note that this project is still in the alpha stage and being actively developed. We welcome various contributions from the community.*

- [ ] Unit tests
- [ ] Richer CLI support
- [ ] Migrate to Rust

## ✨ Features

- 🤖 **Multi-LLM Support**: Works with OpenAI and Anthropic official APIs
- 🛠️ **Rich Tool Ecosystem**: File editing, bash execution, sequential thinking, and more
- 🎯 **Interactive Mode**: Conversational interface for iterative development
- 📊 **Trajectory Recording**: Detailed logging of all agent actions for debugging and analysis
- ⚙️ **Flexible Configuration**: JSON-based configuration with environment variable support
- 🚀 **Easy Installation**: Simple pip-based installation

## 🚀 Quick Start

### Installation

We strongly recommend using [UV](https://docs.astral.sh/uv/) to setup the project.

```bash
git clone <repository-url>
cd trae-agent
uv sync
```

```bash
# Install from source
git clone <repository-url>
cd trae-agent
pip install -e .
```

### Setup API Keys

Set your API keys as environment variables:

```bash
# For OpenAI
export OPENAI_API_KEY="your-openai-api-key"

# For Anthropic
export ANTHROPIC_API_KEY="your-anthropic-api-key"
```

This can also be configured using the trae_config.json file.

### Basic Usage

```bash
# Run a simple task
trae run "Create a hello world Python script"

# Start interactive mode
trae interactive

# Show available tools
trae tools

# Show current configuration
trae show-config
```

## 📖 Usage

### Command Line Interface

The main entry point is the `trae` command with several subcommands:

#### `trae run` - Execute a Task

```bash
# Basic task execution
trae run "Create a Python script that calculates fibonacci numbers"

# With specific provider and model
trae run "Fix the bug in main.py" --provider anthropic --model claude-sonnet-4-20250514

# With custom working directory
trae run "Add unit tests for the utils module" --working-dir /path/to/project

# Save trajectory for debugging
trae run "Refactor the database module" --trajectory-file debug_session.json

# Force to generate patches
trae run "Update the API endpoints" --must-patch
```

#### `trae interactive` - Interactive Mode

```bash
# Start interactive session
trae interactive

# With custom configuration
trae interactive --provider openai --model gpt-4o --max-steps 30
```

In interactive mode, you can:
- Type any task description to execute it
- Use `status` to see agent information
- Use `help` for available commands
- Use `clear` to clear the screen
- Use `exit` or `quit` to end the session

#### `trae show-config` - Configuration Status

```bash
trae show-config

# With custom config file
trae show-config --config-file my_config.json
```

### Configuration

Trae Agent uses a JSON configuration file (`trae_config.json`) for settings:

```json
{
  "default_provider": "anthropic",
  "max_steps": 20,
  "model_providers": {
    "openai": {
      "api_key": "your_openai_api_key",
      "model": "gpt-4o",
      "max_tokens": 128000,
      "temperature": 0.5,
      "top_p": 1
    },
    "anthropic": {
      "api_key": "your_anthropic_api_key", 
      "model": "claude-sonnet-4-20250514",
      "max_tokens": 4096,
      "temperature": 0.5,
      "top_p": 1,
      "top_k": 0
    }
  }
}
```

**Configuration Priority:**
1. Command-line arguments (highest)
2. Configuration file values
3. Environment variables
4. Default values (lowest)

### Environment Variables

- `OPENAI_API_KEY` - OpenAI API key
- `ANTHROPIC_API_KEY` - Anthropic API key

## 🛠️ Available Tools

Trae Agent comes with several built-in tools:

- **str_replace_based_edit_tool**: Create, edit, view, and manipulate files
  - `view` - Display file contents or directory listings
  - `create` - Create new files
  - `str_replace` - Replace text in files
  - `insert` - Insert text at specific lines

- **bash**: Execute shell commands and scripts
  - Run commands with persistent state
  - Handle long-running processes
  - Capture output and errors

- **sequential_thinking**: Structured problem-solving and analysis
  - Break down complex problems
  - Iterative thinking with revision capabilities
  - Hypothesis generation and verification

- **task_done**: Signal task completion
  - Mark tasks as successfully completed
  - Provide final results and summaries

## 📊 Trajectory Recording

Trae Agent automatically records detailed execution trajectories for debugging and analysis:

```bash
# Auto-generated trajectory file
trae run "Debug the authentication module"
# Saves to: trajectory_20250612_220546.json

# Custom trajectory file
trae run "Optimize the database queries" --trajectory-file optimization_debug.json
```

Trajectory files contain:
- **LLM Interactions**: All messages, responses, and tool calls
- **Agent Steps**: State transitions and decision points
- **Tool Usage**: Which tools were called and their results
- **Metadata**: Timestamps, token usage, and execution metrics

For more details, see [TRAJECTORY_RECORDING.md](TRAJECTORY_RECORDING.md).

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests for new functionality
6. Commit your changes (`git commit -m 'Add amazing feature'`)
7. Push to the branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

### Development Guidelines

- Follow PEP 8 style guidelines
- Add tests for new features
- Update documentation as needed
- Use type hints where appropriate
- Ensure all tests pass before submitting

## 📋 Requirements

- Python 3.12+
- OpenAI API key (for OpenAI models)
- Anthropic API key (for Anthropic models)

## 🔧 Troubleshooting

### Common Issues

**Import Errors:**
```bash
# Try setting PYTHONPATH
PYTHONPATH=. trae run "your task"
```

**API Key Issues:**
```bash
# Verify your API keys are set
echo $OPENAI_API_KEY
echo $ANTHROPIC_API_KEY

# Check configuration
trae show-config
```

**Permission Errors:**
```bash
# Ensure proper permissions for file operations
chmod +x /path/to/your/project
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

We thank Anthropic for building the [anthropic-quickstart](https://github.com/anthropics/anthropic-quickstarts) project that served as a valuable reference for the tool ecosystem.
