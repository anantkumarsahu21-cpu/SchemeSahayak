import importlib
import os
import sys


def test_backend_app_imports_from_repo_root():
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

    for name in ["app", "backend", "backend.app", "backend.app.main"]:
        sys.modules.pop(name, None)

    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)

    backend_dir = os.path.join(repo_root, "backend")
    if backend_dir in sys.path:
        sys.path.remove(backend_dir)

    module = importlib.import_module("backend.app.main")

    assert hasattr(module, "app")
