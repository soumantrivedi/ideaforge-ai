"""Database package for migrations and connection management."""
# Re-export functions from database.py to maintain backward compatibility
import sys
from pathlib import Path

# Import from parent database.py module
backend_path = Path(__file__).parent.parent
database_module_path = backend_path / "database.py"

if database_module_path.exists():
    import importlib.util
    spec = importlib.util.spec_from_file_location("database_module", database_module_path)
    database_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(database_module)
    
    # Re-export commonly used functions
    get_db = database_module.get_db
    get_db_with_user = database_module.get_db_with_user
    init_db = database_module.init_db
    check_db_health = database_module.check_db_health
    DATABASE_URL = database_module.DATABASE_URL
    AsyncSessionLocal = database_module.AsyncSessionLocal
    Base = database_module.Base
    engine = database_module.engine
else:
    # Fallback if database.py doesn't exist
    raise ImportError("database.py not found")

