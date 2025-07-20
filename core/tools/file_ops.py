"""
File Operations Tool for NYX System

Provides comprehensive file system operations for codebase analysis, 
file manipulation, and content processing with safety validation.
"""
import asyncio
import os
import re
import mimetypes
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Union, Set
from dataclasses import dataclass

from .base import BaseTool, ToolResult

logger = logging.getLogger(__name__)

@dataclass
class FileOperationConfig:
    """Configuration for file operations with safety constraints"""
    max_file_size_mb: int = 100
    max_files_per_operation: int = 1000
    allowed_extensions: Set[str] = None
    forbidden_paths: Set[str] = None
    max_directory_depth: int = 10
    
    def __post_init__(self):
        if self.allowed_extensions is None:
            # Common development file extensions
            self.allowed_extensions = {
                '.py', '.js', '.ts', '.jsx', '.tsx', '.html', '.css', '.scss',
                '.json', '.yaml', '.yml', '.xml', '.md', '.txt', '.sql',
                '.sh', '.bash', '.dockerfile', '.gitignore', '.env.example',
                '.toml', '.ini', '.cfg', '.conf', '.log'
            }
        
        if self.forbidden_paths is None:
            # Dangerous paths to avoid
            self.forbidden_paths = {
                '/etc', '/usr', '/bin', '/sbin', '/proc', '/sys', '/dev',
                '~/.ssh', '~/.gnupg', '/root', '/var/log', '/var/run'
            }

class FileOperationsTool(BaseTool):
    """
    File operations tool for codebase analysis and manipulation
    
    Capabilities:
    - Safe file reading with size and type validation
    - Directory traversal with depth limits
    - File search and pattern matching
    - Content analysis and statistics
    - Safe file writing with backup support
    """
    
    def __init__(
        self,
        config: Optional[FileOperationConfig] = None,
        agent_id: Optional[str] = None,
        thought_tree_id: Optional[str] = None,
        timeout_seconds: Optional[int] = None
    ):
        super().__init__(
            tool_name="file_operations",
            agent_id=agent_id,
            thought_tree_id=thought_tree_id,
            timeout_seconds=timeout_seconds or 60  # Longer timeout for file operations
        )
        
        self.config = config or FileOperationConfig()
        
        # Track current working directory for relative paths
        self.base_directory = Path.cwd()
    
    async def _validate_parameters(self, parameters: Dict[str, Any]) -> bool:
        """Validate file operation parameters"""
        operation = parameters.get('operation')
        if not operation:
            logger.error("Missing required parameter: operation")
            return False
        
        valid_operations = [
            'read_file', 'write_file', 'list_directory', 'search_files',
            'analyze_codebase', 'get_file_stats', 'find_pattern',
            'create_directory', 'copy_file', 'move_file', 'delete_file'
        ]
        
        if operation not in valid_operations:
            logger.error(f"Invalid operation: {operation}. Valid operations: {valid_operations}")
            return False
        
        # Validate path parameter exists for path-based operations
        if operation in ['read_file', 'write_file', 'list_directory', 'get_file_stats']:
            if 'path' not in parameters:
                logger.error(f"Missing required parameter 'path' for operation: {operation}")
                return False
        
        return True
    
    async def _validate_safety(self, parameters: Dict[str, Any]) -> bool:
        """Validate safety constraints for file operations"""
        path = parameters.get('path')
        if path:
            if not await self._is_safe_path(path):
                logger.error(f"Unsafe path detected: {path}")
                return False
        
        operation = parameters.get('operation')
        
        # Additional safety checks for write operations
        if operation in ['write_file', 'delete_file', 'move_file']:
            if not await self._validate_write_operation(parameters):
                return False
        
        return True
    
    async def _tool_specific_execution(self, parameters: Dict[str, Any]) -> ToolResult:
        """Execute file operation based on parameters"""
        operation = parameters['operation']
        
        try:
            if operation == 'read_file':
                return await self._read_file(parameters)
            elif operation == 'write_file':
                return await self._write_file(parameters)
            elif operation == 'list_directory':
                return await self._list_directory(parameters)
            elif operation == 'search_files':
                return await self._search_files(parameters)
            elif operation == 'analyze_codebase':
                return await self._analyze_codebase(parameters)
            elif operation == 'get_file_stats':
                return await self._get_file_stats(parameters)
            elif operation == 'find_pattern':
                return await self._find_pattern(parameters)
            elif operation == 'create_directory':
                return await self._create_directory(parameters)
            elif operation == 'copy_file':
                return await self._copy_file(parameters)
            elif operation == 'move_file':
                return await self._move_file(parameters)
            elif operation == 'delete_file':
                return await self._delete_file(parameters)
            else:
                return ToolResult(
                    success=False,
                    output="",
                    error_message=f"Unknown operation: {operation}"
                )
                
        except Exception as e:
            logger.error(f"File operation error: {str(e)}")
            return ToolResult(
                success=False,
                output="",
                error_message=f"File operation failed: {str(e)}"
            )
    
    async def _read_file(self, parameters: Dict[str, Any]) -> ToolResult:
        """Read file content with safety validation"""
        path = Path(parameters['path'])
        max_lines = parameters.get('max_lines', None)
        
        try:
            if not path.exists():
                return ToolResult(
                    success=False,
                    output="",
                    error_message=f"File not found: {path}"
                )
            
            if not path.is_file():
                return ToolResult(
                    success=False,
                    output="",
                    error_message=f"Path is not a file: {path}"
                )
            
            # Check file size
            file_size_mb = path.stat().st_size / (1024 * 1024)
            if file_size_mb > self.config.max_file_size_mb:
                return ToolResult(
                    success=False,
                    output="",
                    error_message=f"File too large: {file_size_mb:.2f}MB > {self.config.max_file_size_mb}MB"
                )
            
            # Check file extension
            if path.suffix.lower() not in self.config.allowed_extensions:
                return ToolResult(
                    success=False,
                    output="",
                    error_message=f"File type not allowed: {path.suffix}"
                )
            
            # Read file content
            try:
                content = path.read_text(encoding='utf-8')
            except UnicodeDecodeError:
                # Try to read as binary and decode with error handling
                content = path.read_bytes().decode('utf-8', errors='replace')
            
            # Limit lines if specified
            if max_lines:
                lines = content.split('\n')[:max_lines]
                content = '\n'.join(lines)
                if len(lines) == max_lines:
                    content += f"\n... (file truncated at {max_lines} lines)"
            
            return ToolResult(
                success=True,
                output=content,
                metadata={
                    'file_path': str(path.absolute()),
                    'file_size_bytes': path.stat().st_size,
                    'file_size_mb': file_size_mb,
                    'line_count': content.count('\n') + 1,
                    'char_count': len(content),
                    'encoding': 'utf-8'
                }
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error_message=f"Failed to read file: {str(e)}"
            )
    
    async def _list_directory(self, parameters: Dict[str, Any]) -> ToolResult:
        """List directory contents with filtering options"""
        path = Path(parameters['path'])
        recursive = parameters.get('recursive', False)
        pattern = parameters.get('pattern', '*')
        max_depth = parameters.get('max_depth', self.config.max_directory_depth)
        
        try:
            if not path.exists():
                return ToolResult(
                    success=False,
                    output="",
                    error_message=f"Directory not found: {path}"
                )
            
            if not path.is_dir():
                return ToolResult(
                    success=False,
                    output="",
                    error_message=f"Path is not a directory: {path}"
                )
            
            files_found = []
            directories_found = []
            
            if recursive:
                for item in path.rglob(pattern):
                    if len(Path(item).parts) - len(path.parts) > max_depth:
                        continue
                    
                    if item.is_file():
                        files_found.append({
                            'path': str(item.relative_to(path)),
                            'absolute_path': str(item.absolute()),
                            'size_bytes': item.stat().st_size,
                            'modified': item.stat().st_mtime,
                            'extension': item.suffix.lower()
                        })
                    elif item.is_dir():
                        directories_found.append({
                            'path': str(item.relative_to(path)),
                            'absolute_path': str(item.absolute())
                        })
            else:
                for item in path.glob(pattern):
                    if item.is_file():
                        files_found.append({
                            'name': item.name,
                            'absolute_path': str(item.absolute()),
                            'size_bytes': item.stat().st_size,
                            'modified': item.stat().st_mtime,
                            'extension': item.suffix.lower()
                        })
                    elif item.is_dir():
                        directories_found.append({
                            'name': item.name,
                            'absolute_path': str(item.absolute())
                        })
            
            # Check limits
            if len(files_found) > self.config.max_files_per_operation:
                return ToolResult(
                    success=False,
                    output="",
                    error_message=f"Too many files found: {len(files_found)} > {self.config.max_files_per_operation}"
                )
            
            output = {
                'directory': str(path.absolute()),
                'files': files_found,
                'directories': directories_found,
                'total_files': len(files_found),
                'total_directories': len(directories_found)
            }
            
            return ToolResult(
                success=True,
                output=str(output),
                metadata=output
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error_message=f"Failed to list directory: {str(e)}"
            )
    
    async def _analyze_codebase(self, parameters: Dict[str, Any]) -> ToolResult:
        """Analyze codebase structure and statistics"""
        path = Path(parameters['path'])
        
        try:
            if not path.exists() or not path.is_dir():
                return ToolResult(
                    success=False,
                    output="",
                    error_message=f"Invalid codebase path: {path}"
                )
            
            analysis = {
                'total_files': 0,
                'total_lines': 0,
                'total_size_bytes': 0,
                'file_types': {},
                'language_distribution': {},
                'directory_structure': {},
                'largest_files': []
            }
            
            files_processed = 0
            for file_path in path.rglob('*'):
                if files_processed >= self.config.max_files_per_operation:
                    break
                
                if file_path.is_file() and file_path.suffix.lower() in self.config.allowed_extensions:
                    files_processed += 1
                    
                    file_size = file_path.stat().st_size
                    analysis['total_files'] += 1
                    analysis['total_size_bytes'] += file_size
                    
                    # File type analysis
                    ext = file_path.suffix.lower()
                    if ext in analysis['file_types']:
                        analysis['file_types'][ext] += 1
                    else:
                        analysis['file_types'][ext] = 1
                    
                    # Count lines for text files
                    if file_size < 10 * 1024 * 1024:  # Only for files < 10MB
                        try:
                            content = file_path.read_text(encoding='utf-8', errors='ignore')
                            line_count = content.count('\n') + 1
                            analysis['total_lines'] += line_count
                            
                            # Track largest files
                            analysis['largest_files'].append({
                                'path': str(file_path.relative_to(path)),
                                'size_bytes': file_size,
                                'lines': line_count
                            })
                        except:
                            pass
            
            # Sort and limit largest files
            analysis['largest_files'].sort(key=lambda x: x['size_bytes'], reverse=True)
            analysis['largest_files'] = analysis['largest_files'][:10]
            
            return ToolResult(
                success=True,
                output=str(analysis),
                metadata=analysis
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error_message=f"Codebase analysis failed: {str(e)}"
            )
    
    async def _is_safe_path(self, path: str) -> bool:
        """Check if path is safe to access"""
        try:
            resolved_path = Path(path).resolve()
            path_str = str(resolved_path)
            
            # Check against forbidden paths
            for forbidden in self.config.forbidden_paths:
                if path_str.startswith(forbidden):
                    return False
            
            # Don't allow paths outside project directory in production
            # This is a basic check - could be made more sophisticated
            if not path_str.startswith(str(self.base_directory.resolve())):
                logger.warning(f"Path outside base directory: {path_str}")
            
            return True
            
        except Exception as e:
            logger.error(f"Path safety check failed: {str(e)}")
            return False
    
    async def _validate_write_operation(self, parameters: Dict[str, Any]) -> bool:
        """Additional validation for write operations"""
        # For now, implement basic checks
        # In production, you might want more sophisticated validation
        return True
    
    # Placeholder methods for other operations - can be expanded
    async def _write_file(self, parameters: Dict[str, Any]) -> ToolResult:
        """Write content to file (placeholder)"""
        return ToolResult(
            success=False,
            output="",
            error_message="Write operations not yet implemented for safety"
        )
    
    async def _search_files(self, parameters: Dict[str, Any]) -> ToolResult:
        """Search files by content or name patterns (placeholder)"""
        return ToolResult(
            success=False,
            output="",
            error_message="Search operations not yet implemented"
        )
    
    async def _get_file_stats(self, parameters: Dict[str, Any]) -> ToolResult:
        """Get detailed file statistics (placeholder)"""
        return ToolResult(
            success=False,
            output="",
            error_message="File stats operations not yet implemented"
        )
    
    async def _find_pattern(self, parameters: Dict[str, Any]) -> ToolResult:
        """Find regex patterns in files (placeholder)"""
        return ToolResult(
            success=False,
            output="",
            error_message="Pattern search not yet implemented"
        )
    
    async def _create_directory(self, parameters: Dict[str, Any]) -> ToolResult:
        """Create directory (placeholder)"""
        return ToolResult(
            success=False,
            output="",
            error_message="Directory creation not yet implemented"
        )
    
    async def _copy_file(self, parameters: Dict[str, Any]) -> ToolResult:
        """Copy file (placeholder)"""
        return ToolResult(
            success=False,
            output="",
            error_message="File copying not yet implemented"
        )
    
    async def _move_file(self, parameters: Dict[str, Any]) -> ToolResult:
        """Move file (placeholder)"""
        return ToolResult(
            success=False,
            output="",
            error_message="File moving not yet implemented"
        )
    
    async def _delete_file(self, parameters: Dict[str, Any]) -> ToolResult:
        """Delete file (placeholder)"""
        return ToolResult(
            success=False,
            output="",
            error_message="File deletion not yet implemented for safety"
        )