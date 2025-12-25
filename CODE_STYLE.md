# Code Style Guidelines

This document defines the coding standards and style guidelines for the Chainlit Agent Starter Kit.

## Python Code Style

### General Principles
- Follow PEP 8 as the base standard
- Prioritize readability and maintainability
- Use descriptive names for variables, functions, and classes
- Keep functions focused and reasonably sized

### Formatting

#### Line Length
- Maximum line length: 88 characters (Black formatter default)
- Break long lines at logical points
- Use parentheses for line continuation when appropriate

#### Indentation
- Use 4 spaces for indentation (no tabs)
- Align continuation lines with opening delimiter

#### Imports
```python
# Standard library imports first
import os
import sys
from pathlib import Path

# Third-party imports second
import pandas as pd
from langchain import LLMChain
import chainlit as cl

# Local application imports last
from app.config import settings
from app.llm.client import get_llm
```

#### String Formatting
- Prefer f-strings for string formatting:
  ```python
  # Good
  message = f"Processing {count} items"
  
  # Avoid
  message = "Processing {} items".format(count)
  message = "Processing %s items" % count
  ```

### Naming Conventions

#### Variables and Functions
- Use `snake_case` for variables and functions
- Use descriptive names that explain purpose
```python
# Good
user_count = get_active_users()
def calculate_total_price(items):
    pass

# Avoid
n = get_users()
def calc(x):
    pass
```

#### Classes
- Use `PascalCase` for class names
- Use descriptive names that indicate purpose
```python
# Good
class DatabaseConnection:
    pass

class UserAuthenticator:
    pass

# Avoid
class db:
    pass
```

#### Constants
- Use `UPPER_SNAKE_CASE` for constants
- Define module-level constants at the top
```python
# Good
MAX_RETRY_ATTEMPTS = 3
DEFAULT_TIMEOUT = 30

# Avoid
maxRetries = 3
```

#### Files and Modules
- Use `snake_case` for file and module names
- Keep names descriptive but concise
- Avoid abbreviations unless widely understood

### Documentation

#### Docstrings
- Use triple quotes for docstrings
- Include purpose, parameters, and return values for functions
```python
def process_user_data(user_id: str, include_history: bool = False) -> dict:
    """
    Process and return user data with optional history.
    
    Args:
        user_id: Unique identifier for the user
        include_history: Whether to include user's action history
        
    Returns:
        Dictionary containing processed user data
        
    Raises:
        UserNotFoundError: If user_id doesn't exist
    """
    pass
```

#### Comments
- Use comments to explain "why", not "what"
- Keep comments up-to-date with code changes
- Use `# TODO:` for temporary code that needs improvement

### Error Handling

#### Exception Handling
```python
# Good - Specific exception handling
try:
    result = process_data(input_data)
except ValidationError as e:
    logger.error(f"Data validation failed: {e}")
    return None
except ProcessingError as e:
    logger.error(f"Processing failed: {e}")
    raise

# Avoid - Bare except clauses
try:
    result = process_data(input_data)
except:
    return None
```

#### Logging
- Use appropriate log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- Include context in log messages
- Use structured logging when possible
```python
import logging

logger = logging.getLogger(__name__)

# Good
logger.info(f"Processing user {user_id} with {len(items)} items")
logger.error(f"Failed to connect to database: {error_message}")

# Avoid
print("Processing user")
logger.info("Error occurred")
```

## Project-Specific Guidelines

### Configuration
- All configuration through environment variables
- Use `app/config/settings.py` for centralized configuration
- Provide sensible defaults where possible
```python
# Good
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db")
DEBUG_MODE = os.getenv("DEBUG", "false").lower() == "true"

# Avoid hardcoded values
DATABASE_URL = "postgresql://localhost/myapp"
```

### Database and Persistence
- Use async/await for database operations
- Handle connection failures gracefully
- Use proper transaction management
```python
# Good
async def save_user_data(user_data: dict) -> bool:
    try:
        async with get_db_connection() as conn:
            await conn.execute(query, user_data)
            await conn.commit()
            return True
    except DatabaseError as e:
        logger.error(f"Failed to save user data: {e}")
        return False
```

### API Integration
- Handle API failures with appropriate fallbacks
- Use timeout settings for external calls
- Implement retry logic for transient failures
```python
# Good
async def call_llm_api(prompt: str) -> str:
    try:
        response = await llm_client.generate(
            prompt, 
            timeout=30,
            max_retries=3
        )
        return response.text
    except APIError as e:
        logger.warning(f"LLM API failed: {e}")
        return "I'm sorry, I'm currently unable to process your request."
```

### Security
- Never log sensitive information
- Validate all user inputs
- Use parameterized queries for database operations
```python
# Good
def authenticate_user(username: str, password: str) -> bool:
    # Hash password before comparison
    hashed_password = hash_password(password)
    logger.info(f"Authentication attempt for user: {username}")
    return check_credentials(username, hashed_password)

# Avoid
def authenticate_user(username: str, password: str) -> bool:
    logger.info(f"Login attempt: {username}:{password}")  # Never log passwords!
```

## File Organization

### Directory Structure
```
app/
├── config/          # Configuration and settings
├── core/           # Core business logic
├── data/           # Data models and repositories
├── llm/            # LLM integration
├── rag/            # RAG implementation
├── security/       # Security utilities
└── ui/             # User interface (Chainlit)
```

### Module Organization
- Keep modules focused on a single responsibility
- Use `__init__.py` files to control public API
- Group related functionality together

### Import Organization
- Use absolute imports from project root
- Avoid circular imports
- Import only what you need

## Testing Guidelines

### Test Structure
- Mirror the source code structure in tests
- Use descriptive test names that explain what is being tested
- Group related tests in classes

### Test Naming
```python
# Good
def test_user_authentication_with_valid_credentials():
    pass

def test_database_connection_handles_timeout():
    pass

# Avoid
def test_auth():
    pass

def test_db():
    pass
```

## Tools and Automation

### Recommended Tools
- **Black**: Code formatting (when ready to adopt)
- **isort**: Import sorting (when ready to adopt)
- **flake8**: Linting (when ready to adopt)
- **mypy**: Type checking (optional, for future enhancement)

### Pre-commit Hooks (Future Enhancement)
When the project is ready for stricter automation:
```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/psf/black
    rev: 22.3.0
    hooks:
      - id: black
  - repo: https://github.com/pycqa/isort
    rev: 5.10.1
    hooks:
      - id: isort
```

## Migration Strategy

Since this is an existing codebase, style improvements should be:
1. **Gradual**: Apply to new code and files being modified
2. **Non-breaking**: Don't refactor working code just for style
3. **Consistent**: Once a pattern is established, follow it

---

These guidelines help maintain code quality and consistency across the project. When in doubt, prioritize readability and maintainability over strict adherence to any single rule.
