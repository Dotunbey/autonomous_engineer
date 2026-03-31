import os
import shutil
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)

class FileSystemTools:
    """
    Atomic file operations with path validation to prevent directory traversal.
    """

    def __init__(self, root_dir: str):
        self.root_dir = os.path.abspath(root_dir)

    def _safe_path(self, path: str) -> str:
        """Ensures the path remains within the project root."""
        absolute_path = os.path.abspath(os.path.join(self.root_dir, path))
        if not absolute_path.startswith(self.root_dir):
            raise PermissionError(f"Access denied: {path} is outside workspace.")
        return absolute_path

    def write_file(self, path: str, content: str) -> str:
        """Writes content to a file, creating directories if needed."""
        target = self._safe_path(path)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with open(target, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Successfully wrote to {path}"

    def read_file(self, path: str) -> str:
        """Reads content from a specific file."""
        target = self._safe_path(path)
        with open(target, "r", encoding="utf-8") as f:
            return f.read()

    def list_files(self, directory: str = ".") -> List[str]:
        """Lists all files in a directory recursively, excluding noise."""
        target = self._safe_path(directory)
        ignore_dirs = {".git", "__pycache__", "node_modules", "venv", ".env"}
        
        file_list = []
        for root, dirs, files in os.walk(target):
            dirs[:] = [d for d in dirs if d not in ignore_dirs]
            for file in files:
                rel_path = os.path.relpath(os.path.join(root, file), self.root_dir)
                file_list.append(rel_path)
        return file_list

    def delete_file(self, path: str) -> str:
        """Removes a file from the workspace."""
        target = self._safe_path(path)
        if os.path.isfile(target):
            os.remove(target)
            return f"Deleted {path}"
        raise FileNotFoundError(f"File {path} not found.")