import importlib.util
from pathlib import Path


def test_indra_download_helpers_exist():
    path = Path(__file__).resolve().parents[1] / "scripts" / "download_models.py"
    spec = importlib.util.spec_from_file_location("download_models", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert module.INDRA_FILES
    assert module.INDRA_BASE.startswith("https://")
    assert callable(module.fetch)


def test_fetch_copies_file(tmp_path):
    path = Path(__file__).resolve().parents[1] / "scripts" / "download_models.py"
    spec = importlib.util.spec_from_file_location("download_models", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    source = tmp_path / "source.bin"
    source.write_bytes(b"model")
    target = tmp_path / "target.bin"
    module.fetch(source.as_uri(), target)
    assert target.read_bytes() == b"model"
