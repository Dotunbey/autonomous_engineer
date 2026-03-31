import logging
from typing import Optional

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

logger = logging.getLogger(__name__)


class TracingManager:
    """
    Manages OpenTelemetry tracing setup to provide distributed tracing
    across the API, Celery Workers, and Agent reasoning loops.
    """

    def __init__(self, service_name: str = "autonomous_engineer") -> None:
        """
        Initializes the tracing manager.

        Args:
            service_name: The name of the service emitting traces.
        """
        self.service_name = service_name
        self._tracer: Optional[trace.Tracer] = None

    def setup_tracing(self, enable_console_export: bool = True) -> None:
        """
        Configures the global tracer provider.

        Args:
            enable_console_export: If True, exports traces to the console (useful for dev).
        """
        try:
            provider = TracerProvider()
            if enable_console_export:
                processor = BatchSpanProcessor(ConsoleSpanExporter())
                provider.add_span_processor(processor)
            
            trace.set_tracer_provider(provider)
            self._tracer = trace.get_tracer(self.service_name)
            logger.info("OpenTelemetry tracing configured successfully.")
        except Exception as e:
            logger.error(f"Failed to setup tracing: {e}")

    @property
    def tracer(self) -> trace.Tracer:
        """
        Gets the configured tracer instance.

        Returns:
            trace.Tracer: The active tracer.
        
        Raises:
            RuntimeError: If tracing hasn't been setup yet.
        """
        if not self._tracer:
            raise RuntimeError("Tracer not initialized. Call setup_tracing() first.")
        return self._tracer


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    manager = TracingManager()
    manager.setup_tracing(enable_console_export=True)
    
    tracer = manager.tracer
    with tracer.start_as_current_span("example_agent_operation") as span:
        span.set_attribute("agent.role", "coder")
        span.add_event("Code generated successfully")
        logger.info("Trace span executed.")
