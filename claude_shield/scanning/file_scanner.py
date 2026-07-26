import os
import time
from typing import List, Iterator
from pathlib import Path

class FileScanner:
    def __init__(self, 
                 workspace_root: str,
                 max_file_size: int = 10 * 1024 * 1024,  # 10 MB
                 max_total_files: int = 10000,
                 max_total_bytes: int = 100 * 1024 * 1024,  # 100 MB
                 max_duration_seconds: int = 30):
        self.workspace_root = Path(workspace_root).resolve()
        self.max_file_size = max_file_size
        self.max_total_files = max_total_files
        self.max_total_bytes = max_total_bytes
        self.max_duration_seconds = max_duration_seconds
        
        self.excludes = {
            '.git', 'node_modules', 'vendor', 'dist', 'build', '.cache', 
            'venv', '.venv', '__pycache__', 'coverage', 'reports', '.claude-shield'
        }
        
    def _is_safe_to_read(self, file_path: Path) -> bool:
        # Prevent path traversal
        try:
            file_path.resolve().relative_to(self.workspace_root)
        except ValueError:
            return False
            
        if file_path.is_symlink() or not file_path.is_file():
            return False
            
        try:
            stat = file_path.stat()
            # Skip if larger than max_file_size
            if stat.st_size > self.max_file_size:
                return False
                
            # Quick binary check by reading first block
            with open(file_path, 'rb') as f:
                chunk = f.read(1024)
                if b'\0' in chunk:
                    return False
                    
            return True
        except Exception:
            return False

    def scan(self) -> Iterator[Path]:
        start_time = time.time()
        files_scanned = 0
        bytes_scanned = 0
        
        for root, dirs, files in os.walk(self.workspace_root, followlinks=False):
            # Check duration
            if time.time() - start_time > self.max_duration_seconds:
                break
                
            # Prune excluded dirs
            dirs[:] = [d for d in dirs if d not in self.excludes]
            
            for file in files:
                if files_scanned >= self.max_total_files:
                    return
                if bytes_scanned >= self.max_total_bytes:
                    return
                    
                path = Path(root) / file
                if self._is_safe_to_read(path):
                    files_scanned += 1
                    bytes_scanned += path.stat().st_size
                    yield path
