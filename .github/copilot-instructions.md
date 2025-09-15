# Knowledge Base AI Coding Instructions

## Project Overview
This is a multi-service knowledge base system built as a MonoRepo with 4 core services:
- `knowledge_sync/`: Document synchronization from GitLab/Confluence
- `knowledge_api/`: FastAPI REST service with Whoosh search
- `knowledge_mcp/`: MCP protocol server for AI assistants  
- `knowledge_common/`: Shared models, config, and utilities

## Architecture Patterns

### Package Structure Convention
All services follow this pattern under `packages/`:
```
packages/
├── knowledge_common/     # Base models, DB, config utilities
├── knowledge_{service}/  # Individual service implementations
    ├── __init__.py
    ├── main.py          # Service entry point
    └── {service}.py     # Core implementation
```

### Database Model Pattern
All models inherit from `BaseModel` in `packages/knowledge_common/models.py`:
```python
class BaseModel(Base):
    id: Mapped[int] = Column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = Column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = Column(DateTime, onupdate=datetime.utcnow)
```

### Configuration System
- Primary config: `config/settings.yaml` (environment-specific overrides in `config/environments/`)
- Source definitions: `config/sources.yml` for GitLab/Confluence sync
- Use `packages/knowledge_common/config.py` settings singleton

## Development Workflows

### Environment Setup
```bash
# Use the setup script (handles virtual env + dependencies)
python tools/scripts/setup.py

# Or manually:
python -m venv venv
source venv/bin/activate  # Linux/Mac
# source venv/Scripts/activate  # Windows Git Bash
pip install -e .[all]
```

### Service Commands
```bash
# Cross-platform launcher (Windows alternative to make)
python run.py {command}

# Available commands:
python run.py dev           # Start API + docs server
python run.py api-start     # API only
python run.py sync-start    # Sync service only  
python run.py mcp-start     # MCP server only
python run.py docs-dev      # MkDocs dev server only
```

### Database Operations
- SQLite database at `data/knowledge_base.db`
- Models use SQLAlchemy 2.0+ async syntax with `Mapped` type hints
- Database session management via `get_db()` async generator from `knowledge_common.database`

## Service Integration Points

### Document Sync Flow
1. `GitLabSyncer`/`ConfluenceSyncer` fetch content → `DocumentModel` records
2. API service rebuilds Whoosh search index from database on startup  
3. Search index stored in `data/search_index/`

### Search Engine Integration
- Whoosh-based with Chinese segmentation (jieba)
- Index rebuilt automatically via `rebuild_search_index()` in API startup
- Search interface: `packages/knowledge_api/search.py`

### MCP Protocol Implementation
- Server exposes `search_knowledge` tool to AI assistants
- Uses same search backend as REST API
- Configured for Claude.ai integration

## Code Conventions

### Error Handling
Use structured logging with context:
```python
from ..knowledge_common.logging import get_logger
logger = get_logger(__name__)

logger.error("Sync failed", project_id=project_id, error=str(e))
```

### Async Patterns
All database operations are async using SQLAlchemy 2.0:
```python
async for session in get_db():
    query = select(DocumentModel).where(DocumentModel.is_published == True)
    result = await session.execute(query)
```

### Service Dependencies
- Install groups: `[api]`, `[sync]`, `[mcp]`, `[all]` 
- Each service has minimal dependencies, shared via `knowledge_common`

## Docker Deployment
- Multi-service setup via `docker/docker-compose.yml`
- SQLite with volume persistence (no external DB required)
- Services: `sync-service`, `api-service`, `mcp-service`, `docs-service`
- Nginx reverse proxy configuration in `docker/nginx.conf`

## Testing
- Test structure mirrors package structure under `tests/`
- Run via `python -m pytest` after installing test dependencies
- Integration tests use real SQLite database with test fixtures