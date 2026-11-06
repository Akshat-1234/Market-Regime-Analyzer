"""Check cleanup never silently loses original research files."""
from hashlib import sha256
import json
from pathlib import Path
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
HISTORY = ROOT / 'historical'


def test_original_files_match_preservation_manifest():
    manifest = json.loads((HISTORY / 'original-project-31902b7.sha256.json').read_text())
    with ZipFile(HISTORY / 'original-project-31902b7.zip') as archive:
        assert set(archive.namelist()) == set(manifest)
        assert archive.testzip() is None
        for name, expected in manifest.items():
            assert sha256(archive.read(name)).hexdigest() == expected, name


def test_arena_archive_is_unchanged():
    path = HISTORY / 'arena-market-regime-platform.zip'
    assert sha256(path.read_bytes()).hexdigest() == 'bdf7b9136f8fd9b52dc6eedd34fd916c74f8baaaccc8815b3bd170dfc948d4b1'
