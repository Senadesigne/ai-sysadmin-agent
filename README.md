# AI SysAdmin Agent Starter Kit

A production-ready Chainlit agent template for building AI-powered system administration tools with authentication, persistence, and optional RAG capabilities.

## Quick Start

### 1. Environment Setup

Copy the environment template and configure your settings:

```bash
# Windows PowerShell
Copy-Item .env.example .env

# macOS/Linux
cp .env.example .env
```

### 2. Configure Authentication

Edit your `.env` file and set the required values:

```bash
# Generate a secure authentication secret
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Copy the generated secret and update your `.env` file:

```env
CHAINLIT_AUTH_SECRET=your-generated-secret-here
AUTH_MODE=prod
DEV_NO_AUTH=false
ADMIN_IDENTIFIER=admin
ADMIN_PASSWORD=your-secure-password-here
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the Application

```bash
chainlit run app/ui/chat.py
```

The application will be available at `http://localhost:8000`

## Features

- **🔐 Configurable Authentication**: Development and production modes with secure credential management
- **💾 Persistent Chat History**: SQLite-based conversation storage with thread management
- **🤖 Optional LLM Integration**: Support for Google Gemini and OpenAI with graceful fallbacks
- **📚 Optional RAG**: Document ingestion and retrieval-augmented generation
- **🛡️ Security**: Command approval patterns and configurable execution policies
- **📊 Inventory Management**: Hardware inventory tracking and querying

## Configuration Options

### Development Mode
For local development with minimal setup:
```env
AUTH_MODE=dev
DEV_NO_AUTH=true
```

### Production Mode
For production deployment with full authentication:
```env
AUTH_MODE=prod
DEV_NO_AUTH=false
ADMIN_IDENTIFIER=your-admin-username
ADMIN_PASSWORD=your-secure-password
```

### Optional Features

#### Enable LLM Functionality
Add your API key to `.env`:
```env
GOOGLE_API_KEY=your-google-api-key
# OR
OPENAI_API_KEY=your-openai-api-key
```

#### Enable RAG (Document Search)
```env
RAG_ENABLED=true
GOOGLE_API_KEY=your-google-api-key  # Required for embeddings
```

## Knowledge Base (RAG)

The application includes optional Retrieval-Augmented Generation (RAG) capabilities for document search and question answering.

### Adding Documents
1. Place your documents in the `app/knowledge_base/` directory
   - Supported formats: `.md`, `.txt`, `.pdf`
   - The starter kit includes sample documents for reference

2. Run the ingestion script to index your documents:
   ```bash
   python scripts/ingest.py
   ```

3. Enable RAG in your `.env` file:
   ```env
   RAG_ENABLED=true
   GOOGLE_API_KEY=your-google-api-key
   ```

### Default Configuration
- **RAG is disabled by default** (`RAG_ENABLED=false`)
- The knowledge base contains only sample documents in the starter kit
- Vector database files are stored in `.data/chroma_db/` (ignored by git)

## Project Structure

```
ai-sysadmin-agent/
├── app/
│   ├── config/          # Configuration and settings
│   ├── core/            # Core business logic
│   ├── data/            # Data models and repositories
│   ├── knowledge_base/  # RAG documents
│   ├── llm/             # LLM client implementations
│   ├── rag/             # RAG engine and processing
│   ├── security/        # Security utilities
│   └── ui/              # Chainlit UI and chat interface
├── public/              # Static assets
├── scripts/             # Utility scripts
├── .env.example         # Environment template
└── requirements.txt     # Python dependencies
```

## Data Storage

All application data is stored in the `.data/` directory:
- `chainlit.db` - Chat history and user sessions
- `inventory.db` - Hardware inventory data
- `chroma_db/` - Vector database for RAG
- `tmp/` - Temporary file uploads

## Security Notes

- Never commit `.env` files to version control
- Use strong passwords in production
- The application includes command approval patterns for safe execution
- All sensitive operations require user confirmation

## Troubleshooting

### Application won't start
1. Verify your `.env` file exists and has the required values
2. Check that `CHAINLIT_AUTH_SECRET` is set
3. Ensure Python dependencies are installed

### Authentication issues
1. Verify `ADMIN_IDENTIFIER` and `ADMIN_PASSWORD` in `.env`
2. Check that `AUTH_MODE` is set correctly
3. For development, you can use `DEV_NO_AUTH=true`

### LLM not working
1. Verify your API key is set in `.env`
2. Check your API quota and billing status
3. The application will work without API keys (with limited functionality)

## License

This is a commercial starter kit. See `LICENSE-COMMERCIAL.md` for terms and conditions.

## Support

For support and documentation, see the included guides:
- `CHAINLIT_SETUP.md` - Detailed setup instructions
- `ARCHITECTURE.md` - System architecture overview
- `env_setup_instructions.txt` - Environment configuration guide
