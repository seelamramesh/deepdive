"""Architecture test: verify no unauthorized AI provider endpoints."""

import ast
import os
import pytest

# Unauthorized provider patterns
BLOCKED_PATTERNS = [
    "api.openai.com",
    "api.anthropic.com",
    "generativelanguage.googleapis.com",
    "api.cohere.ai",
    "api-inference.huggingface.co",
]

ALLOWED_MESH_URL = "api.meshapi.ai"


def get_python_files():
    """Collect all .py files under app/."""
    py_files = []
    for root, dirs, files in os.walk("app"):
        for f in files:
            if f.endswith(".py"):
                py_files.append(os.path.join(root, f))
    return py_files


class TestMeshCompliance:
    def test_no_direct_provider_urls(self):
        """Ensure no Python file references unauthorized AI endpoints."""
        violations = []
        for filepath in get_python_files():
            with open(filepath) as f:
                content = f.read()
            for pattern in BLOCKED_PATTERNS:
                if pattern in content:
                    violations.append(f"{filepath}: contains {pattern}")
        assert violations == [], f"Unauthorized AI endpoints found:\n" + "\n".join(violations)

    def test_mesh_url_present(self):
        """Verify Mesh API URL is used in the gateway."""
        with open("app/core/mesh_gateway.py") as f:
            content = f.read()
        assert ALLOWED_MESH_URL in content or "mesh_base_url" in content

    def test_no_direct_openai_client(self):
        """Ensure OpenAI client always uses Mesh base_url."""
        for filepath in get_python_files():
            with open(filepath) as f:
                content = f.read()
            # If file imports OpenAI, it must set base_url
            if "from openai import" in content or "import openai" in content:
                if "AsyncOpenAI(" in content or "OpenAI(" in content:
                    assert "base_url" in content, (
                        f"{filepath}: creates OpenAI client without base_url override"
                    )

    def test_all_python_files_compile(self):
        """Check all Python files are free of syntax errors."""
        for filepath in get_python_files():
            with open(filepath) as f:
                source = f.read()
            try:
                ast.parse(source, filename=filepath)
            except SyntaxError as e:
                pytest.fail(f"Syntax error in {filepath}: {e}")

    def test_no_env_file_committed(self):
        """Verify .env is in .gitignore."""
        with open(".gitignore") as f:
            gitignore = f.read()
        assert ".env" in gitignore
