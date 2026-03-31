import logging
from typing import Dict, Any
try:
    from tools.docker import DockerSandbox
except ImportError:
    DockerSandbox = None

logger = logging.getLogger(__name__)

class TerminalTools:
    """
    Provides shell execution capabilities isolated inside a Docker sandbox.
    """

    def __init__(self, workspace_dir: str):
        """
        Args:
            workspace_dir: The host directory to mount into the sandbox.
        """
        self.workspace = workspace_dir
        # Fallback if Docker sandbox isn't fully wired yet
        self.sandbox = DockerSandbox() if DockerSandbox else None

    def run_shell_command(self, command: str) -> str:
        """
        Executes a bash command safely.

        Args:
            command: The raw shell command string.

        Returns:
            STDOUT or STDERR from the execution.
        """
        logger.info(f"Terminal requested command: {command}")
        
        if not self.sandbox:
            logger.warning("DockerSandbox not initialized. Running in unsafe local mode is disabled.")
            return "Execution blocked: Sandbox unavailable."

        result = self.sandbox.execute(command, workdir="/app")
        
        if result.is_timeout:
            return f"Error: Command timed out after {self.sandbox._timeout} seconds."
        
        if result.exit_code != 0:
            return f"Exit Code {result.exit_code}\nError: {result.stderr}"
            
        return result.stdout or "Command executed successfully with no output."