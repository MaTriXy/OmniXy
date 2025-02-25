# Contributing to OmniXy

Welcome to OmniXy - the universal Model Context Protocol (MCP) client!

We're thrilled you're interested in contributing to this advanced LLM integration framework. Your expertise will help us maintain our position at the forefront of model-agnostic AI systems.

## Ways to Contribute

We welcome contributions of all kinds! Here are some ways you can help:

1. **Add New Model Integrations:** Create new notebooks showcasing novel model integration methods.
2. **Improve Core Functionality:** Enhance, update, or expand our MCP protocol implementation.
3. **Fix Bugs:** Help us squash bugs in existing code or protocol implementations.
4. **Enhance Documentation:** Improve clarity, add examples, or fix typos in our docs.
5. **Share Creative Ideas:** Have an innovative idea for model integration or protocol extensions?
6. **Engage in Discussions:** Participate in our community to help shape the future of OmniXy.

Remember, no contribution is too small. Every improvement helps make this repository an even better resource for the community.

## Reporting Issues

Found a problem or have a suggestion? Please create an issue on GitHub, providing as much detail as possible.

## Contributing Code or Content

1. **Fork and Branch:** Fork the repository and create your branch from `main`.
2. **Make Your Changes:** Implement your contribution, following our best practices.
3. **Test:** Ensure your changes work as expected.
4. **Follow the Style:** Adhere to the coding and documentation conventions used throughout the project.
5. **Commit:** Make your git commits informative and concise.
6. **Stay Updated:** The main branch is frequently updated. Before opening a pull request, make sure your code is up-to-date with the current main branch and has no conflicts.
7. **Push and Pull Request:** Push to your fork and submit a pull request.
8. **Discuss:** Use the community channels to discuss your contribution if you need feedback or have questions.

## Environment Setup

1. Install uv:

   ```bash
   brew install uv  # or pipx install uv
   ```

2. Install dependencies:

   ```bash
   uv pip install -r requirements-dev.txt
   ```

3. Configure pre-commit:

   ```bash
   uv run pre-commit install
   ```

## Adding New Components

### 1. Drivers

**Purpose:** Implementations for specific model providers

**Requirements:**

- Inherit from BaseDriver
- Support MCP specification v1.2+
- Handle authentication via env variables
- Implement error handling
- Include unit tests

**File Location:** `src/drivers/[provider_name]/`

### 2. Plugins

**Purpose:** Extend protocol capabilities

**Requirements:**

- Use plugin decorators
- Maintain backward compatibility
- Document new features
- Include demo notebooks

**File Location:** `src/plugins/[plugin_name]/`

### 3. Workflows

**Purpose:** Complex execution patterns

**Requirements:**

- Use workflow DSL
- Support checkpointing
- Include validation steps
- Document resource requirements

**File Location:** `src/workflows/[workflow_name]/`

## Code Quality and Readability

To ensure the highest quality and readability of our code:

1. **Write Clean Code:** Follow best practices for clean, readable code.
2. **Use Comments:** Add clear and concise comments to explain complex logic.
3. **Format Your Code:** Use consistent formatting throughout your contribution.
4. **Language Model Review:** After completing your code, consider passing it through a language model for additional formatting and readability improvements. This extra step can help make your code even more accessible and maintainable.

## Documentation

Clear documentation is crucial. Whether you're improving existing docs or adding new ones, follow the same process: fork, change, test, and submit a pull request.

## Final Notes

We're grateful for all our contributors and excited to see how you'll help expand the world's most comprehensive MCP offerings.
Don't hesitate to ask questions if you're unsure about anything.
