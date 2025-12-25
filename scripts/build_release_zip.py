#!/usr/bin/env python3
"""
Build Release ZIP Script for AI SysAdmin Agent Starter Kit

Creates a reproducible release ZIP package using a whitelist approach.
Excludes databases, cache files, and temporary data.
"""

import os
import sys
import zipfile
import argparse
from pathlib import Path
from datetime import datetime


def get_project_root():
    """Get the project root directory (parent of scripts/)."""
    return Path(__file__).parent.parent


def should_include_file(file_path, project_root):
    """
    Determine if a file should be included in the release ZIP.
    Uses whitelist approach with specific exclusions.
    """
    # Convert to relative path from project root
    try:
        rel_path = file_path.relative_to(project_root)
    except ValueError:
        return False
    
    rel_path_str = str(rel_path).replace('\\', '/')
    
    # BLACKLIST - Always exclude these patterns
    blacklist_patterns = [
        '.git/',
        '.github/',
        '.venv/',
        '__pycache__/',
        '.pyc',
        '.data/',
        '.db',
        '.sqlite3',
        '.bin',
        'chroma.sqlite3',
        'logs/',
        '.log',
        '.pdf',
        'chainlit.db',
        'inventory.db',
    ]
    
    # Check blacklist patterns
    for pattern in blacklist_patterns:
        if pattern in rel_path_str or rel_path_str.endswith(pattern.replace('/', '')):
            return False
    
    # WHITELIST - Include these paths
    whitelist_patterns = [
        'app/',
        'scripts/',
        'public/',
        'README.md',
        'CHAINLIT_SETUP.md', 
        'STARTER_KIT_PLAN.md',
        'LICENSE-COMMERCIAL.md',
        'COMMERCIAL-TERMS.md',
        'THIRD_PARTY_NOTICES.md',
        'CONTRIBUTING.md',
        'CODE_STYLE.md',
        'requirements.txt',
        'pyproject.toml',
        'poetry.lock',
        'chainlit.md',
        '.env.example',
    ]
    
    # Check if file matches whitelist
    for pattern in whitelist_patterns:
        if rel_path_str.startswith(pattern) or rel_path_str == pattern:
            # Special exclusions within app/
            if rel_path_str.startswith('app/data/'):
                return False
            if 'chroma_db' in rel_path_str:
                return False
            return True
    
    return False


def collect_files(project_root):
    """Collect all files that should be included in the release."""
    included_files = []
    
    for root, dirs, files in os.walk(project_root):
        # Skip hidden directories and common exclusions
        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['__pycache__', 'node_modules']]
        
        for file in files:
            file_path = Path(root) / file
            if should_include_file(file_path, project_root):
                included_files.append(file_path)
    
    return sorted(included_files)


def create_release_zip(output_dir, files, project_root):
    """Create the release ZIP file."""
    # Ensure output directory exists
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate ZIP filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_filename = f"starter-kit-release-{timestamp}.zip"
    zip_path = output_dir / zip_filename
    
    # Create ZIP file
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as zipf:
        for file_path in files:
            # Calculate relative path for archive
            rel_path = file_path.relative_to(project_root)
            
            # Add file to ZIP
            zipf.write(file_path, rel_path)
    
    return zip_path, len(files)


def get_top_level_items(zip_path):
    """Get top-level items in the ZIP for summary."""
    top_level_items = set()
    
    with zipfile.ZipFile(zip_path, 'r') as zipf:
        for name in zipf.namelist():
            # Get first component of path
            parts = name.split('/')
            if parts[0]:  # Skip empty parts
                top_level_items.add(parts[0])
    
    return sorted(top_level_items)


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description='Build release ZIP for AI SysAdmin Agent')
    parser.add_argument('--out', default='dist', help='Output directory (default: dist)')
    
    args = parser.parse_args()
    
    project_root = get_project_root()
    
    print("[BUILD] Building AI SysAdmin Agent Release ZIP...")
    print(f"[INFO] Project root: {project_root}")
    print(f"[INFO] Output directory: {args.out}")
    print()
    
    # Collect files
    print("[COLLECT] Collecting files...")
    files = collect_files(project_root)
    
    if not files:
        print("[ERROR] No files found to include in release!")
        sys.exit(1)
    
    print(f"[SUCCESS] Found {len(files)} files to include")
    print()
    
    # Create ZIP
    print("[ZIP] Creating ZIP file...")
    zip_path, file_count = create_release_zip(args.out, files, project_root)
    
    # Get summary
    top_level_items = get_top_level_items(zip_path)
    
    # Print results
    print("[SUCCESS] Release ZIP created successfully!")
    print()
    print("[SUMMARY] Release Summary:")
    print(f"   ZIP Path: {zip_path}")
    print(f"   Files: {file_count}")
    print(f"   Size: {zip_path.stat().st_size / 1024:.1f} KB")
    print()
    print("[CONTENTS] Top-level items in ZIP:")
    for item in top_level_items:
        print(f"   - {item}")
    print()
    print("[DONE] Ready for distribution!")


if __name__ == '__main__':
    main()
