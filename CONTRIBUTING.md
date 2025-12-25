# Contributing Guidelines

This document outlines the development workflow and standards for the Chainlit Agent Starter Kit.

## Development Setup

### Prerequisites
- Python 3.8 or higher
- Virtual environment (recommended)

### Initial Setup
1. Clone the repository
2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Copy environment configuration:
   ```bash
   cp .env.example .env
   ```
5. Configure your `.env` file with appropriate values
6. Run the verification script:
   ```bash
   python scripts/verify_startup.py
   ```

## Branching Strategy

### Branch Types
- `main` - Production-ready code
- `develop` - Integration branch for features
- `feature/feature-name` - New features
- `fix/issue-description` - Bug fixes
- `docs/documentation-update` - Documentation changes

### Workflow
1. Create feature branch from `develop`:
   ```bash
   git checkout develop
   git pull origin develop
   git checkout -b feature/your-feature-name
   ```
2. Make your changes
3. Test thoroughly
4. Create pull request to `develop`
5. After review and approval, merge to `develop`
6. Periodically merge `develop` to `main` for releases

## Commit Standards

### Commit Message Format
```
type(scope): brief description

Longer description if needed

- Additional details
- Breaking changes noted
```

### Commit Types
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

### Examples
```
feat(auth): add configurable authentication modes

- Support for dev and production auth modes
- Environment-based credential configuration
- Backward compatibility maintained

fix(rag): handle missing API keys gracefully

- Implement NullRagEngine fallback
- Add clear user messaging for disabled features

docs(readme): update setup instructions

chore(deps): update langchain to latest version
```

## Pull Request Checklist

Before submitting a pull request, ensure:

### Code Quality
- [ ] Code follows project style guidelines (see CODE_STYLE.md)
- [ ] No hardcoded credentials or sensitive data
- [ ] Error handling is appropriate and user-friendly
- [ ] Comments explain complex logic

### Testing
- [ ] Manual testing completed
- [ ] No breaking changes to existing functionality
- [ ] Database migrations tested (if applicable)
- [ ] Works with and without API keys

### Documentation
- [ ] README updated if setup process changed
- [ ] Code comments added for complex sections
- [ ] Configuration changes documented

### Environment
- [ ] `.env.example` updated with new variables
- [ ] No local development files committed
- [ ] Dependencies updated in `requirements.txt` if needed

## Code Review Process

### For Reviewers
1. Check functionality and logic
2. Verify security considerations
3. Ensure code style compliance
4. Test major changes locally
5. Provide constructive feedback

### For Contributors
1. Address all review comments
2. Update PR description if scope changes
3. Rebase if requested to maintain clean history
4. Notify reviewers when ready for re-review

## Development Standards

### File Organization
- Keep modules focused and cohesive
- Use clear, descriptive file and function names
- Maintain consistent directory structure

### Configuration Management
- All configuration through environment variables
- Use `.env.example` as template
- No hardcoded values in production code

### Error Handling
- Graceful degradation when services unavailable
- Clear, user-friendly error messages
- Proper logging for debugging

### Security
- No credentials in code or documentation
- Validate all user inputs
- Follow principle of least privilege

## Getting Help

### Resources
- Check existing issues and documentation first
- Review CODE_STYLE.md for style guidelines
- Run `python scripts/verify_startup.py` for environment validation

### Communication
- Use clear, descriptive issue titles
- Provide reproduction steps for bugs
- Include environment details when relevant

## Release Process

### Version Numbering
- Follow semantic versioning (MAJOR.MINOR.PATCH)
- Major: Breaking changes
- Minor: New features, backward compatible
- Patch: Bug fixes

### Release Checklist
- [ ] All tests passing
- [ ] Documentation updated
- [ ] Version numbers updated
- [ ] Release notes prepared
- [ ] Commercial license compliance verified

---

Thank you for contributing to the Chainlit Agent Starter Kit!
