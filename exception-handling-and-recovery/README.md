# Exception Handling and Recovery Pattern (Google ADK)

This directory demonstrates the **Exception Handling and Recovery Pattern** in multi-agent workflows using the **Google Agent Development Kit (ADK)** (`google-adk`).

---

## 🎯 Pattern Overview

When building complex agentic systems, failures in external tools, APIs, or data sources are inevitable (e.g., service outages, rate limits, invalid inputs, unmapped queries). Instead of crashing or returning an unhelpful generic error, robust agentic workflows implement **Exception Handling and Recovery**:

1. **Transient Resilience (`RetryConfig`)**: The workflow engine automatically retries transient errors at the node level before declaring failure.
2. **Graceful Degradation (Fallback Recovery)**: When high-precision primary services encounter an exception, specialized fallback agents dynamically trigger broader, alternative recovery strategies.
3. **Transparent Communication**: Downstream agents synthesize the results while clearly informing the user about the degradation level or apology if recovery was exhausted.

---

## 🏗️ Architecture

```
                       +-------------------+
                       |       START       |
                       +---------+---------+
                                 |
                                 v
                     +-----------------------+
                     |    primary_handler    |
                     |  (Precise Geocoding)  |
                     +-----------+-----------+
                                 |
                     Writes to session state:
                     - primary_location_failed (bool)
                     - primary_error (str | None)
                     - location_result (dict | None)
                                 |
                                 v
                     +-----------------------+
                     |   fallback_handler    |
                     |  (City Area Recovery) |
                     +-----------+-----------+
                                 |
                     If primary failed:
                     - Calls get_general_area_info
                     - Sets fallback_used = True
                     - Degrades to city centroid
                                 |
                                 v
                     +-----------------------+
                     |    response_agent     |
                     |  (Final Synthesis)    |
                     +-----------------------+
```

---

## 🔑 Session State Management

Shared state across agents in the pipeline:

| Key | Type | Description |
|---|---|---|
| `primary_location_failed` | `bool` | Flag indicating whether the precise geocoding tool threw an exception or failed |
| `primary_error` | `str \| None` | Error message and exception type captured from the primary lookup |
| `fallback_used` | `bool` | Flag indicating whether fallback recovery was triggered and succeeded |
| `recovery_strategy` | `str \| None` | Active recovery strategy (e.g., `"city_centroid_degradation"`, `"exhausted"`) |
| `location_result` | `dict \| None` | The resolved geospatial payload (precise or approximate fallback) |

---

## 🚀 How to Run

### 1. Run the Default Exception & Fallback Recovery Scenario
```bash
cd /home/ollama/python/pattern/exception-handling-and-recovery
uv run python main.py
```

### 2. Run All Demonstration Scenarios
```bash
uv run python main.py --all
```

### 3. Test a Custom Query
```bash
# Test successful precise street lookup
uv run python main.py "Find location for 1600 Amphitheatre Pkwy, Mountain View, CA"

# Test fallback recovery (unmapped address in known city)
uv run python main.py "Find location for 9999 Nonexistent Error St, Seattle, WA"

# Test unresolvable/fictional location
uv run python main.py "Where is 42 Unknown Boulevard, Atlantis?"
```

