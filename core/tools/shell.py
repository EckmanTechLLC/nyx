"""
Shell Command Tool for NYX System

Provides safe shell command execution with comprehensive safety validation,
output capture, and error handling for development workflows.
"""
import asyncio
import os
import shlex
import logging
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, List, Set
from dataclasses import dataclass

from .base import BaseTool, ToolResult

logger = logging.getLogger(__name__)

@dataclass
class ShellCommandConfig:
    """Configuration for shell command execution with safety constraints"""
    max_execution_time_seconds: int = 300
    max_output_size_mb: int = 10
    allowed_commands: Set[str] = None
    forbidden_commands: Set[str] = None
    allowed_directories: Set[str] = None
    require_explicit_approval: bool = True
    capture_environment: bool = False
    
    def __post_init__(self):
        if self.allowed_commands is None:
            # Common safe development commands
            self.allowed_commands = {
                # Basic commands
                'echo', 'true', 'false', 'test',
                
                # File operations
                'ls', 'cat', 'head', 'tail', 'grep', 'find', 'wc', 'sort', 'uniq',
                'file', 'stat', 'du', 'df', 'pwd', 'which', 'type',
                
                # Development tools
                'git', 'npm', 'pip', 'python', 'python3', 'node', 'yarn',
                'cargo', 'rustc', 'go', 'javac', 'java', 'mvn', 'gradle',
                
                # Build tools
                'make', 'cmake', 'gcc', 'clang', 'docker', 'docker-compose',
                
                # Text processing
                'sed', 'awk', 'tr', 'cut', 'paste', 'diff', 'patch',
                
                # Archive tools
                'tar', 'zip', 'unzip', 'gzip', 'gunzip',
                
                # System info (read-only)
                'ps', 'top', 'htop', 'free', 'uname', 'whoami', 'id',
                'date', 'cal', 'uptime', 'env', 'printenv'
            }
        
        if self.forbidden_commands is None:
            # Dangerous commands that should never be executed
            self.forbidden_commands = {
                # System modification
                'rm', 'rmdir', 'mv', 'cp', 'chmod', 'chown', 'chgrp',
                'sudo', 'su', 'passwd', 'useradd', 'userdel', 'groupadd',
                
                # Network and system control
                'kill', 'killall', 'pkill', 'shutdown', 'reboot', 'halt',
                'systemctl', 'service', 'mount', 'umount', 'fdisk',
                
                # Package management (could be dangerous)
                'apt', 'apt-get', 'yum', 'dnf', 'pacman', 'brew',
                
                # File editors that could hang
                'vi', 'vim', 'emacs', 'nano',
                
                # Network tools that could be misused
                'wget', 'curl', 'ssh', 'scp', 'rsync', 'ftp', 'telnet',
                
                # Compression that could consume resources
                'dd', 'sync'
            }

class ShellCommandTool(BaseTool):
    """
    Shell command execution tool with comprehensive safety validation
    
    Capabilities:
    - Safe command execution with whitelist/blacklist filtering
    - Output capture with size limits
    - Working directory control
    - Environment variable management
    - Comprehensive logging and error handling
    """
    
    def __init__(
        self,
        config: Optional[ShellCommandConfig] = None,
        working_directory: Optional[str] = None,
        agent_id: Optional[str] = None,
        thought_tree_id: Optional[str] = None,
        timeout_seconds: Optional[int] = None
    ):
        super().__init__(
            tool_name="shell_command",
            agent_id=agent_id,
            thought_tree_id=thought_tree_id,
            timeout_seconds=timeout_seconds or 300  # 5 minute default timeout
        )
        
        self.config = config or ShellCommandConfig()
        
        # Working directory management
        if working_directory:
            self.working_directory = Path(working_directory).resolve()
        else:
            self.working_directory = Path.cwd()
        
        # Track command history for learning
        self.command_history: List[Dict[str, Any]] = []
    
    async def _validate_parameters(self, parameters: Dict[str, Any]) -> bool:
        """Validate shell command parameters"""
        command = parameters.get('command')
        if not command:
            logger.error("Missing required parameter: command")
            return False
        
        if not isinstance(command, str):
            logger.error("Command parameter must be a string")
            return False
        
        if not command.strip():
            logger.error("Command cannot be empty")
            return False
        
        return True
    
    async def _validate_safety(self, parameters: Dict[str, Any]) -> bool:
        """Comprehensive safety validation for shell commands"""
        command = parameters['command'].strip()
        
        # Parse command to extract the base command
        try:
            parsed_command = shlex.split(command)
            if not parsed_command:
                logger.error("Empty command after parsing")
                return False
            
            base_command = parsed_command[0]
            
            # Remove path prefixes to get command name
            base_command = os.path.basename(base_command)
            
        except ValueError as e:
            logger.error(f"Failed to parse command: {str(e)}")
            return False
        
        # Check against forbidden commands first
        if base_command in self.config.forbidden_commands:
            logger.error(f"Forbidden command detected: {base_command}")
            return False
        
        # Check against allowed commands if whitelist is enabled
        if self.config.allowed_commands and base_command not in self.config.allowed_commands:
            logger.error(f"Command not in allowed list: {base_command}")
            return False
        
        # Additional safety checks
        if not await self._validate_command_safety(command, parsed_command):
            return False
        
        # Validate working directory if specified
        working_dir = parameters.get('working_directory')
        if working_dir:
            if not await self._validate_working_directory(working_dir):
                return False
        
        return True
    
    async def _validate_command_safety(self, command: str, parsed_command: List[str]) -> bool:
        """Additional command safety validation"""
        
        # Check for dangerous patterns
        dangerous_patterns = [
            r'rm\s+-[rf]+',  # rm -rf patterns
            r'>\s*/dev/',    # Writing to device files
            r'&\s*$',        # Background execution
            r'\|\|\|',       # Suspicious pipe chains
            r';\s*rm',       # Command chaining with rm
            r'`.*`',         # Command substitution
            r'\$\(',         # Command substitution
            r'sudo',         # Sudo usage
            r'su\s+',        # Switch user
            r'/etc/passwd',  # System file access
            r'/etc/shadow',  # System file access
        ]
        
        import re
        for pattern in dangerous_patterns:
            if re.search(pattern, command, re.IGNORECASE):
                logger.error(f"Dangerous command pattern detected: {pattern}")
                return False
        
        # Check for suspicious arguments
        suspicious_args = ['-rf', '--force', '--recursive', '-p', '--parents']
        for arg in parsed_command[1:]:  # Skip the command itself
            if arg in suspicious_args:
                logger.warning(f"Potentially dangerous argument detected: {arg}")
                # Don't fail, just warn - some legitimate uses exist
        
        return True
    
    async def _validate_working_directory(self, working_dir: str) -> bool:
        """Validate working directory safety"""
        try:
            working_path = Path(working_dir).resolve()
            
            # Check if directory exists
            if not working_path.exists() or not working_path.is_dir():
                logger.error(f"Working directory does not exist: {working_dir}")
                return False
            
            # Check against allowed directories if configured
            if self.config.allowed_directories:
                working_str = str(working_path)
                allowed = False
                for allowed_dir in self.config.allowed_directories:
                    if working_str.startswith(allowed_dir):
                        allowed = True
                        break
                
                if not allowed:
                    logger.error(f"Working directory not allowed: {working_dir}")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to validate working directory: {str(e)}")
            return False
    
    async def _tool_specific_execution(self, parameters: Dict[str, Any]) -> ToolResult:
        """Execute shell command with comprehensive safety and monitoring"""
        command = parameters['command'].strip()
        working_dir = parameters.get('working_directory', str(self.working_directory))
        env_vars = parameters.get('environment', {})
        capture_stderr = parameters.get('capture_stderr', True)
        
        # Prepare execution environment
        execution_env = os.environ.copy()
        if env_vars:
            execution_env.update(env_vars)
        
        try:
            logger.info(f"Executing shell command: {command} (cwd: {working_dir})")
            
            # Execute command with timeout and output capture
            process = await asyncio.create_subprocess_shell(
                command,
                cwd=working_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE if capture_stderr else asyncio.subprocess.DEVNULL,
                env=execution_env,
                limit=self.config.max_output_size_mb * 1024 * 1024  # Convert MB to bytes
            )
            
            try:
                stdout_data, stderr_data = await asyncio.wait_for(
                    process.communicate(),
                    timeout=self.config.max_execution_time_seconds
                )
            except asyncio.TimeoutError:
                # Kill the process if it times out
                try:
                    process.kill()
                    await process.wait()
                except:
                    pass  # Process might already be dead
                
                return ToolResult(
                    success=False,
                    output="",
                    error_message=f"Command timed out after {self.config.max_execution_time_seconds} seconds",
                    stderr="Command execution timeout"
                )
            
            # Decode output
            stdout_text = stdout_data.decode('utf-8', errors='replace') if stdout_data else ""
            stderr_text = stderr_data.decode('utf-8', errors='replace') if stderr_data else ""
            
            # Check output size limits
            total_output_size = len(stdout_text) + len(stderr_text)
            max_size_bytes = self.config.max_output_size_mb * 1024 * 1024
            
            if total_output_size > max_size_bytes:
                # Truncate output if too large
                remaining_size = max_size_bytes
                if len(stdout_text) > remaining_size // 2:
                    stdout_text = stdout_text[:remaining_size // 2] + "\n... (stdout truncated)"
                remaining_size -= len(stdout_text)
                if len(stderr_text) > remaining_size:
                    stderr_text = stderr_text[:remaining_size] + "\n... (stderr truncated)"
            
            # Determine success based on return code
            success = process.returncode == 0
            
            # Prepare result
            result = ToolResult(
                success=success,
                output=stdout_text,
                stderr=stderr_text,
                error_message=None if success else f"Command failed with exit code {process.returncode}",
                metadata={
                    'command': command,
                    'working_directory': working_dir,
                    'return_code': process.returncode,
                    'stdout_size': len(stdout_text),
                    'stderr_size': len(stderr_text),
                    'environment_vars': list(env_vars.keys()) if env_vars else [],
                    'execution_timeout': self.config.max_execution_time_seconds
                }
            )
            
            # Log command execution for learning
            self.command_history.append({
                'command': command,
                'working_directory': working_dir,
                'return_code': process.returncode,
                'success': success,
                'output_size': total_output_size,
                'timestamp': asyncio.get_event_loop().time()
            })
            
            logger.info(f"Command completed: return_code={process.returncode}, success={success}")
            
            return result
            
        except Exception as e:
            logger.error(f"Shell command execution failed: {str(e)}")
            return ToolResult(
                success=False,
                output="",
                error_message=f"Command execution error: {str(e)}",
                metadata={
                    'command': command,
                    'working_directory': working_dir,
                    'error_type': type(e).__name__
                }
            )
    
    async def get_command_statistics(self) -> Dict[str, Any]:
        """Get statistics about command execution history"""
        if not self.command_history:
            return {'message': 'No command history available'}
        
        total_commands = len(self.command_history)
        successful_commands = sum(1 for cmd in self.command_history if cmd['success'])
        
        # Most common commands
        command_counts = {}
        for cmd in self.command_history:
            base_cmd = cmd['command'].split()[0] if cmd['command'].split() else 'unknown'
            command_counts[base_cmd] = command_counts.get(base_cmd, 0) + 1
        
        most_common = sorted(command_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        
        return {
            'total_commands_executed': total_commands,
            'successful_commands': successful_commands,
            'success_rate': successful_commands / total_commands if total_commands > 0 else 0.0,
            'most_common_commands': most_common,
            'average_output_size': sum(cmd['output_size'] for cmd in self.command_history) / total_commands,
            'working_directories': list(set(cmd['working_directory'] for cmd in self.command_history))
        }
    
    def set_working_directory(self, directory: str):
        """Change the default working directory for commands"""
        new_dir = Path(directory).resolve()
        if new_dir.exists() and new_dir.is_dir():
            self.working_directory = new_dir
            logger.info(f"Working directory changed to: {self.working_directory}")
        else:
            logger.error(f"Invalid working directory: {directory}")
            raise ValueError(f"Directory does not exist: {directory}")
    
    def get_working_directory(self) -> str:
        """Get the current working directory"""
        return str(self.working_directory)