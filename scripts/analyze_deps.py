import importlib.metadata
import sys

packages = [
    "langchain",
    "langchain-core",
    "langchain-community",
    "langchain-google-genai",
    "google-generativeai",
    "pydantic",
    "numpy"
]

print(f"Python: {sys.version}")
print("-" * 30)
for pkg in packages:
    try:
        ver = importlib.metadata.version(pkg)
        print(f"{pkg}: {ver}")
    except importlib.metadata.PackageNotFoundError:
        print(f"{pkg}: NOT INSTALLED")
print("-" * 30)

# Check specific import causing the latest crash
try:
    from langchain_core import pydantic_v1
    print("langchain_core.pydantic_v1: FOUND")
except ImportError as e:
    print(f"langchain_core.pydantic_v1: MISSING ({e})")
