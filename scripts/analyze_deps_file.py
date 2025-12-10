import importlib.metadata
import sys

packages = [
    "langchain",
    "langchain-core",
    "langchain-community",
    "langchain-google-genai",
    "google-generativeai",
    "pydantic",
    "numpy",
    "chainlit"
]

with open("deps_report.txt", "w") as f:
    f.write(f"Python: {sys.version}\n")
    f.write("-" * 30 + "\n")
    for pkg in packages:
        try:
            ver = importlib.metadata.version(pkg)
            f.write(f"{pkg}: {ver}\n")
        except importlib.metadata.PackageNotFoundError:
            f.write(f"{pkg}: NOT INSTALLED\n")
    f.write("-" * 30 + "\n")

    # Check specific import causing the latest crash
    try:
        from langchain_core import pydantic_v1
        f.write("langchain_core.pydantic_v1: FOUND\n")
    except ImportError as e:
        f.write(f"langchain_core.pydantic_v1: MISSING ({e})\n")
    except Exception as e:
        f.write(f"langchain_core.pydantic_v1: ERROR ({e})\n")
