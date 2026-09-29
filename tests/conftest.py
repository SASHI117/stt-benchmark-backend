import os
import sys
import tempfile
from pathlib import Path

# The engine is created at import time, so point it at a throwaway SQLite
# file before any application module is imported.
_db_dir = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{Path(_db_dir, 'test.db').as_posix()}"

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
