"""
Test isolation: point every on-disk store at a throwaway directory.

Runs before any test module imports the app (discovery uses `-t .`, which makes
`tests` a package), so `settings` and module-level paths pick these up instead of
the developer's real data/ folder (metrics.db, generated files, caption cache).
"""

import atexit
import os
import shutil
import tempfile
from pathlib import Path

_TMP = Path(tempfile.mkdtemp(prefix="transcriptflow-tests-"))
os.environ["METRICS_DB_PATH"] = str(_TMP / "metrics.db")
os.environ["FILE_STORAGE_DIR"] = str(_TMP / "files")
os.environ["TRANSCRIPT_CACHE_DIR"] = str(_TMP / "transcript_cache")

atexit.register(shutil.rmtree, _TMP, ignore_errors=True)
