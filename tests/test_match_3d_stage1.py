import json
import struct
from pathlib import Path

MATCH_TEMPLATE = Path("app/templates/match.html")
STATIC = Path("app/static")


def _glb_json(path: Path) -> dict:
    data = path.read_bytes()
    assert data[:4] == b"glTF"
    version = struct.unpack("<I", data[4:8])[0]
    declared_length = struct.unpack("<I", data[8:12])[0]
    assert version == 2
    assert declared_length == len(data)

    chunk_length, chunk_type = struct.unpack("<II", data[12:20])
    assert chunk_type == 0x4E4F534A
    return json.loads(data[20:20 + chunk_length].decode("utf-8").rstrip("\x00 "))


def test_stage1_files_are_local_and_present():
    expected = (
        STATIC / "vendor/model-viewer/model-viewer.min.js",
        STATIC / "vendor/model-viewer/config.js",
        STATIC / "match/stadium-3d-poc.js",
        STATIC / "match/stadium-3d-poc.css",
        STATIC / "match/assets/footy-match-stadium-v1.glb",
    )
    for path in expected:
        assert path.is_file(), path


def test_match_template_keeps_2d_and_adds_live_3d_canvas():
    source = MATCH_TEMPLATE.read_text()
    for name in ("match-canvas", "match-visual-stage", "match-2d-shell", "match-view-switcher", "match-3d-shell", "match-3d-canvas"):
        assert f'id="{name}"' in source
    assert "data-model-src=" in source
    assert "<model-viewer" not in source
    assert "vendor/model-viewer" not in source
    assert "match/bootstrap.js" in source


def test_stage1_bootstrap_is_presentation_only_and_fail_open():
    source = (STATIC / "match/stadium-3d-poc.js").read_text()

    assert 'getContext("webgl2"' in source
    assert 'getContext("webgl"' in source
    assert '"error"' in source
    assert "MODEL_LOAD_TIMEOUT_MS" in source
    assert 'setView("2d")' in source
    assert "button3d.disabled = true" in source

    forbidden = (
        "fetch(",
        "XMLHttpRequest",
        "advance_match",
        "complete_match",
        "visualEndpoint",
        "data-complete-endpoint",
        "data-advance-endpoint",
        "localStorage",
        "sessionStorage",
    )
    for token in forbidden:
        assert token not in source


def test_stage1_runtime_configuration_never_points_to_third_party_hosts():
    source = (STATIC / "vendor/model-viewer/config.js").read_text()
    assert "https://" not in source
    assert "http://" not in source
    assert "/static/vendor/model-viewer/draco/" in source
    assert "/static/vendor/model-viewer/basis/" in source
    assert "/static/vendor/model-viewer/lottie/" in source


def test_stadium_glb_is_self_contained_and_does_not_need_optional_decoders():
    doc = _glb_json(STATIC / "match/assets/footy-match-stadium-v1.glb")

    assert "KHR_draco_mesh_compression" not in doc.get("extensionsUsed", [])
    assert "KHR_texture_basisu" not in doc.get("extensionsUsed", [])

    external_uris = [
        item["uri"]
        for group in ("buffers", "images")
        for item in doc.get(group, [])
        if item.get("uri")
    ]
    assert external_uris == []

    names = {node.get("name") for node in doc.get("nodes", [])}
    assert "MatchBall" in names
    for side in ("home", "away"):
        for number in range(1, 12):
            assert f"{side}_{number:02d}" in names

def test_live_3d_loads_independently_of_hidden_canvas():
    source = (STATIC / "match/bootstrap.js").read_text()
    assert 'await import("./three-renderer.js")' in source
    assert "renderer.init();" in source
    assert "createRendererBridge" in source
