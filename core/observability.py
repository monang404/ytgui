from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter


COMMAND_COUNT = Counter(
    "ytplayer_commands_total",
    "Total number of commands executed",
    ["command_name", "status"]
)

COMMAND_LATENCY = Histogram(
    "ytplayer_command_duration_seconds",
    "Duration of command execution in seconds",
    ["command_name"]
)

EVENT_COUNT = Counter("ytgui_events_total", "Total events published", ["event_type"])

ACTIVE_WEBSOCKETS = Gauge(
    "ytplayer_active_websockets",
    "Number of currently active WebSocket connections",
)

def setup_tracing():
    provider = TracerProvider()
    trace.set_tracer_provider(provider)
    return trace.get_tracer("ytplayer.core")

tracer = setup_tracing()

def get_metrics_content():
    """Returns the Prometheus metrics in text format."""
    return generate_latest(), CONTENT_TYPE_LATEST
