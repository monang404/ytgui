from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

# --- Prometheus Metrics ---

# 1. Total Command Executions (Counter)
COMMAND_COUNT = Counter(
    "ytplayer_commands_total",
    "Total number of commands executed",
    ["command_name", "status"]
)

# 2. Command Latency (Histogram)
COMMAND_LATENCY = Histogram(
    "ytplayer_command_duration_seconds",
    "Duration of command execution in seconds",
    ["command_name"]
)

# 3. Domain Events Published (Counter)
EVENT_COUNT = Counter("ytgui_events_total", "Total events published", ["event_type"])

# 4. Active WebSockets (Gauge)
ACTIVE_WEBSOCKETS = Gauge(
    "ytplayer_active_websockets",
    "Number of currently active WebSocket connections",
)

# --- OpenTelemetry Tracing ---
def setup_tracing():
    provider = TracerProvider()
    processor = BatchSpanProcessor(ConsoleSpanExporter())
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)
    return trace.get_tracer("ytplayer.core")

tracer = setup_tracing()

def get_metrics_content():
    """Returns the Prometheus metrics in text format."""
    return generate_latest(), CONTENT_TYPE_LATEST
