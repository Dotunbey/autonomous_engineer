import logging
import subprocess
from dataclasses import dataclass
from typing import List, Optional

logger = logging.getLogger(__name__)

@dataclass(frozen=True)
class ExecutionResult:
    """Stores the outcome of a sandboxed execution."""
    stdout: str
    stderr: str
    exit_code: int
    is_timeout: bool = False

class DockerSandbox:
    """
    Provides secure, isolated execution of shell commands using Docker containers.
    """

    def __init__(self, image: str = "python:3.9-slim", timeout: int = 30):
        """
        Initializes the sandbox with a specific image and timeout.

        Args:
            image: The Docker image to use for the sandbox.
            timeout: Maximum seconds allowed for execution.
        """
        self._image = image
        self._timeout = timeout

    def execute(self, command: str, workdir: str = "/app") -> ExecutionResult:
        """
        Runs a command inside a temporary Docker container.

        Args:
            command: The shell command to execute.
            workdir: The working directory inside the container.

        Returns:
            An ExecutionResult object containing output and exit codes.
        """
        # Wrapping command to handle environment or path issues if necessary
        docker_cmd = [
            "docker", "run", "--rm",
            "-v", f"{workdir}:{workdir}",
            "-w", workdir,
            self._image,
            "sh", "-c", command
        ]

        try:
            logger.info(f"Executing in sandbox: {command}")
            process = subprocess.run(
                docker_cmd,
                capture_output=True,
                text=True,
                timeout=self._timeout
            )
            return ExecutionResult(
                stdout=process.stdout,
                stderr=process.stderr,
                exit_code=process.returncode
            )
        except subprocess.TimeoutExpired as e:
            logger.warning(f"Execution timed out after {self._timeout}s")
            return ExecutionResult(
                stdout=e.stdout.decode() if e.stdout else "",
                stderr=e.stderr.decode() if e.stderr else "TIMEOUT",
                exit_code=124,
                is_timeout=True
            )
        except Exception as e:
            logger.error(f"Sandbox failure: {str(e)}")
            return ExecutionResult(stdout="", stderr=str(e), exit_code=1)

if __name__ == "__main__":
    sandbox = DockerSandbox()
    # Example: Running a simple python script in the sandbox
    result = sandbox.execute("python3 -c 'print(\"Hello from Sandbox\")'")
    print(f"Status: {result.exit_code}, Output: {result.stdout.strip()}")


