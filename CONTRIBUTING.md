# Contributing to X-Agent

Thank you for your interest in contributing to X-Agent! This document provides guidelines for contributing to the project.

## Development Setup

1. **Fork and clone the repository**:
```bash
git clone https://github.com/YOUR_USERNAME/X-Agent.git
cd X-Agent
```

2. **Install dependencies**:
```bash
make install-dev
```

3. **Set up environment**:
```bash
cp .env.example .env
# Edit .env with your configuration
```

4. **Run tests**:
```bash
make test
```

## Development Workflow

1. **Create a branch**:
```bash
git checkout -b feature/your-feature-name
```

2. **Make your changes**:
- Follow the existing code style
- Add tests for new functionality
- Update documentation as needed

3. **Format and lint**:
```bash
make format
make lint
```

4. **Run tests**:
```bash
make test
```

5. **Commit your changes**:
```bash
git commit -m "Add feature: description"
```

6. **Push and create a Pull Request**:
```bash
git push origin feature/your-feature-name
```

## Code Style

- Use **Black** for code formatting (line length: 100)
- Follow **PEP 8** guidelines
- Use **type hints** for function signatures
- Write **docstrings** for public APIs

## Testing

- Write unit tests for new functionality
- Maintain test coverage above 80%
- Use **pytest** for testing
- Follow the existing test structure

## Documentation

- Update README.md for user-facing changes
- Update docs/ for architectural changes
- Add docstrings to new functions and classes
- Include usage examples

## Pull Request Guidelines

- Provide a clear description of changes
- Reference related issues
- Ensure all tests pass
- Keep PRs focused and reasonably sized
- Update CHANGELOG.md if applicable

## Areas for Contribution

- **Core Features**: Enhance cognitive loop, planning, execution
- **Tools**: Add new tool implementations
- **Memory**: Improve memory management and retrieval
- **Security**: Enhance policy layer and sandboxing
- **Documentation**: Improve guides and examples
- **Tests**: Increase test coverage
- **Performance**: Optimize critical paths

## Questions?

Feel free to open an issue for questions or discussions!
