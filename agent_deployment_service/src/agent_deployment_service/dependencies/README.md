# Dependencies Layer Architecture

## Purpose
FastAPI dependency injection for cross-cutting concerns.

## Module Structure

### `app_deps.py` - Application Dependencies
- **Settings injection**: Cached application configuration
- **Database sessions**: Async session management
- **Service instances**: Shared service initialization
- **Infrastructure**: Logging, metrics, monitoring

### `user_deps.py` - Authentication & Authorization  
- **User JWT validation**: Verify end-user tokens
- **M2M authentication**: Machine-to-machine tokens
- **Permission checks**: Role-based access control
- **Token extraction**: OAuth2 bearer tokens

### `m2m_deps.py` - Machine-to-Machine Auth
- **Service-to-service auth**: Internal API calls
- **API key validation**: External service authentication
- **Rate limiting**: Per-service quotas

## Usage Pattern

```python
from fastapi import Depends
from ..dependencies import get_current_user, get_db_session, get_settings

@router.post("/deploy")
async def deploy_agent(
    user: UserTokenData = Depends(get_current_user),  # Auth
    db: AsyncSession = Depends(get_db_session),        # Database
    settings: Settings = Depends(get_settings),        # Config
):
    # Business logic here
    pass
```

## Best Practices
1. Keep dependencies pure (no side effects in initialization)
2. Use caching for expensive operations (settings, connections)
3. Separate concerns (auth vs infrastructure vs business)
4. Prefer composition over inheritance
