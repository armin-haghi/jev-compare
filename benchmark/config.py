import hashlib
import importlib
import json
import os
import re
from pathlib import Path
import yaml


def load_env(path=".env"):
    """Minimal non-executing dotenv loader; existing environment wins."""
    if Path(path).exists():
        for line in Path(path).read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.removeprefix("export ").split("=", 1)
                os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


def read_yaml(path):
    return yaml.safe_load(Path(path).read_text())


def resolve(value):
    if isinstance(value, dict):
        return {k: resolve(v) for k, v in value.items()}
    if isinstance(value, list):
        return [resolve(v) for v in value]
    if isinstance(value, str):
        def replace(match):
            key = match.group(1)
            if not os.environ.get(key):
                raise ValueError(f"Required environment variable is empty: {key}")
            return os.environ[key]
        return re.sub(r"\$\{([A-Z_0-9]+)\}", replace, value)
    return value


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def file_hash(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_case(name):
    if not re.fullmatch(r"[a-zA-Z_][a-zA-Z_0-9.]*", name):
        raise ValueError("Invalid case module")
    module = importlib.import_module(name if "." in name else f"cases.{name}")
    for method in ("prepare", "load_records", "build_payload", "candidates", "is_correct"):
        if not callable(getattr(module, method, None)):
            raise TypeError(f"Case does not implement {method}")
    return module


def json_write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")
