# 🤝 Contributing to CFB 27 Rules Bot

Thank you for your interest in contributing to Harry, the CFB 27 Rules Bot! We welcome contributions from the community.

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Making Changes](#making-changes)
- [Pull Request Process](#pull-request-process)
- [Issue Reporting](#issue-reporting)
- [Feature Requests](#feature-requests)

## 📜 Code of Conduct

This project follows the CFB 27 League's code of conduct:

- **Be respectful** and inclusive
- **Be constructive** in feedback and discussions
- **Be patient** with new contributors
- **Be collaborative** and help others learn

## 🚀 Getting Started

### Prerequisites

- Python 3.8+
- Git
- Discord Bot Token
- Basic understanding of Discord.py

### Development Setup

1. **Fork the repository**
   ```bash
   git clone https://github.com/YOUR_USERNAME/cfb-rules-bot.git
   cd cfb-rules-bot
   ```

2. **Create a virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   cp env.example .env
   # Edit .env with your development tokens
   ```

## 🔧 Making Changes

### Code Style

- Follow PEP 8 Python style guidelines
- Use meaningful variable and function names
- Add comments for complex logic
- Keep functions focused and small

### File Structure

```
cfb-rules-bot/
├── bot.py                 # Main bot application
├── ai_integration.py      # AI service integration
├── google_docs_integration.py  # Google Docs API
├── data/                  # Configuration files
├── logs/                  # Log files (gitignored)
├── tests/                 # Test files
└── docs/                  # Documentation
```

### Adding New Features

1. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**
   - Add new commands in `bot.py`
   - Update documentation
   - Add tests if applicable

3. **Test your changes**
   ```bash
   python3 bot.py
   # Test in your development Discord server
   ```

4. **Commit your changes**
   ```bash
   git add .
   git commit -m "Add: your feature description"
   ```

### Adding New Commands

To add a new slash command:

```python
@bot.tree.command(name="your_command", description="Command description")
async def your_command(interaction: discord.Interaction, parameter: str):
    """Your command implementation"""
    await interaction.response.send_message("Your response")
```

### Adding New Rivalry Responses

To add new rivalry responses:

```python
rivalry_keywords = {
    'your_keyword': 'Your response! 🎉',
    # ... existing responses
}
```

## 📝 Pull Request Process

### Before Submitting

1. **Test your changes** thoroughly
2. **Update documentation** if needed
3. **Check for linting errors**
4. **Ensure all tests pass**

### Pull Request Template

```markdown
## Description
Brief description of your changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Documentation update
- [ ] Code refactoring

## Testing
- [ ] Tested locally
- [ ] Tested in development Discord server
- [ ] No breaking changes

## Screenshots (if applicable)
Add screenshots of your changes

## Additional Notes
Any additional information
```

### Review Process

1. **Automated checks** will run on your PR
2. **Maintainers** will review your code
3. **Feedback** will be provided if needed
4. **Approval** and merge when ready

## 🐛 Issue Reporting

### Bug Reports

When reporting bugs, please include:

- **Description**: Clear description of the bug
- **Steps to reproduce**: How to reproduce the issue
- **Expected behavior**: What should happen
- **Actual behavior**: What actually happens
- **Environment**: Python version, OS, etc.
- **Logs**: Relevant error messages or logs

### Issue Template

```markdown
**Bug Description**
A clear description of the bug

**Steps to Reproduce**
1. Go to '...'
2. Click on '....'
3. See error

**Expected Behavior**
What you expected to happen

**Actual Behavior**
What actually happened

**Environment**
- Python version: 3.x
- OS: Windows/macOS/Linux
- Bot version: x.x.x

**Additional Context**
Any other relevant information
```

## 💡 Feature Requests

### Suggesting Features

We welcome feature requests! Please:

1. **Check existing issues** first
2. **Describe the feature** clearly
3. **Explain the use case** and benefits
4. **Consider implementation** complexity

### Feature Request Template

```markdown
**Feature Description**
A clear description of the feature

**Use Case**
Why would this feature be useful?

**Proposed Implementation**
How do you think this should work?

**Additional Context**
Any other relevant information
```

## 🧪 Testing

### Running Tests

```bash
# Run all tests
python -m pytest tests/

# Run specific test
python -m pytest tests/test_bot.py

# Run with coverage
python -m pytest --cov=bot tests/
```

### Writing Tests

```python
import pytest
from unittest.mock import Mock, AsyncMock

@pytest.mark.asyncio
async def test_your_function():
    # Your test implementation
    pass
```

## 📚 Documentation

### Updating Documentation

- Update `README.md` for major changes
- Update `SETUP.md` for setup changes
- Add inline comments for complex code
- Update command descriptions

### Documentation Standards

- Use clear, concise language
- Include code examples
- Add screenshots when helpful
- Keep documentation up to date

## 🏷️ Release Process

### Version Numbering

We use semantic versioning: `MAJOR.MINOR.PATCH`

- **MAJOR**: Breaking changes
- **MINOR**: New features
- **PATCH**: Bug fixes

### Release Checklist

- [ ] Update version numbers
- [ ] Update changelog
- [ ] Test all features
- [ ] Update documentation
- [ ] Create release notes

## 🆘 Getting Help

### Resources

- **Discord**: Join the CFB 27 League Discord
- **GitHub Issues**: For bug reports and feature requests
- **Documentation**: Check README and SETUP guides

### Contact

- **League Commissioners**: For league-specific questions
- **Maintainers**: For technical questions
- **Community**: For general discussion

## 🙏 Recognition

Contributors will be recognized in:

- **README.md** contributors section
- **Release notes** for significant contributions
- **League Discord** announcements

Thank you for contributing to the CFB 27 Rules Bot! 🏈

---

**Happy coding!** 🚀
