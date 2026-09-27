"""Offline deployment must contain every transitive renderer module."""
import hashlib
import json
import re
from pathlib import Path

def test_three_vendor_manifest_and_local_import_closure():
    root = Path('app/static/vendor/three')
    manifest = json.loads((root / 'manifest.json').read_text())
    assert manifest['version'] == '0.186.0'
    for entry in manifest['files']:
        data = (root / entry['file']).read_bytes()
        assert hashlib.sha256(data).hexdigest() == entry['sha256']
    for module in root.glob('*.js'):
        for specifier in re.findall(r"(?m)^import\b[^;]*?\bfrom\s*['\"]([^'\"]+)['\"]", re.sub(r"/\*.*?\*/", "", module.read_text(), flags=re.S)):
            assert specifier.startswith('./'), (module, specifier)
            assert (module.parent / specifier).is_file()

def test_live_renderer_never_owns_authoritative_match_requests_or_another_loop():
    for name in ('three-renderer.js', 'match-scene.js', 'player-model.js', 'renderer-bridge.js'):
        source = (Path('app/static/match') / name).read_text()
        for forbidden in ('requestAnimationFrame', 'advanceEndpoint', 'completeEndpoint'):
            assert forbidden not in source, (name, forbidden)
