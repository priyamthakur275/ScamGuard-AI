"""Create local configuration without replacing existing settings or secrets."""
from pathlib import Path
import secrets

root = Path(__file__).resolve().parent
backend_env = root / 'backend' / '.env'
if not backend_env.exists():
    backend_env.write_text(
        'APP_ENV=development\nDEBUG=false\n'
        f'SECRET_KEY={secrets.token_urlsafe(48)}\n'
        'ML_SERVICE_URL=\nCORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000\n',
        encoding='utf-8',
    )
    print('Created backend/.env with a private local key and the existing SQLite default.')
else:
    print('Kept existing backend/.env unchanged.')
frontend_env = root / 'frontend' / '.env.local'
if not frontend_env.exists():
    frontend_env.write_text('APP_SERVICE_URL=http://127.0.0.1:8000\n', encoding='utf-8')
    print('Configured the frontend to use your local backend.')
else:
    print('Kept existing frontend/.env.local unchanged.')
print('Install dependencies, then start the backend and frontend as described in START_HERE.md.')
