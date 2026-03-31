import re
import os
from typing import List, Dict, Any

class SearchEngineTools:
    """
    Structural and semantic search capabilities for large codebases.
    """

    def __init__(self, root_dir: str):
        self.root_dir = root_dir

    def grep_search(self, pattern: str, file_extension: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Performs a regex search across the codebase.
        Matches Claude Code's ability to locate symbols without full indexing.
        """
        results = []
        regex = re.compile(pattern)
        
        for root, _, files in os.walk(self.root_dir):
            for file in files:
                if file_extension and not file.endswith(file_extension):
                    continue
                
                path = os.path.join(root, file)
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        for i, line in enumerate(f, 1):
                            if regex.search(line):
                                results.append({
                                    "file": os.path.relpath(path, self.root_dir),
                                    "line": i,
                                    "content": line.strip()
                                })
                except Exception:
                    continue
        return results

    def find_definitions(self, symbol_name: str) -> List[Dict[str, Any]]:
        """
        Naive AST-like search for class or function definitions.
        """
        # Look for 'class Symbol' or 'def Symbol'
        pattern = rf"(class|def)\s+{symbol_name}[\s\(:]"
        return self.grep_search(pattern)