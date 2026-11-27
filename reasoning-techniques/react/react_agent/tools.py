"""Tools and utilities for Reasoning and Acting (ReAct) agent.

Provides structured tools for:
1. Knowledge base search (enterprise facts, infrastructure, services, personnel)
2. Safe mathematical calculations
3. System telemetry and metrics lookup
4. Structured database record retrieval
"""

from __future__ import annotations

import ast
import math
import operator
from typing import Any, Dict, List, Optional, Union
from google.adk.tools import FunctionTool

# ---------------------------------------------------------------------------
# Safe Mathematical Evaluator
# ---------------------------------------------------------------------------

SAFE_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}

SAFE_FUNCTIONS = {
    "abs": abs,
    "round": round,
    "min": min,
    "max": max,
    "sqrt": math.sqrt,
    "log": math.log,
    "log10": math.log10,
    "exp": math.exp,
    "ceil": math.ceil,
    "floor": math.floor,
}

SAFE_CONSTANTS = {
    "pi": math.pi,
    "e": math.e,
}


def _safe_eval(node: ast.AST) -> Union[int, float]:
    """Recursively evaluates an AST node with whitelisted math operations."""
    if isinstance(node, ast.Expression):
        return _safe_eval(node.body)
    elif isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return node.value
        raise ValueError(f"Unsupported constant literal: {node.value!r}")
    elif isinstance(node, ast.Name):
        if node.id in SAFE_CONSTANTS:
            return SAFE_CONSTANTS[node.id]
        raise ValueError(f"Undefined variable in expression: {node.id}")
    elif isinstance(node, ast.BinOp):
        op_type = type(node.op)
        if op_type not in SAFE_OPERATORS:
            raise ValueError(f"Unsupported binary operator: {op_type.__name__}")
        left = _safe_eval(node.left)
        right = _safe_eval(node.right)
        if op_type in (ast.Div, ast.FloorDiv, ast.Mod) and right == 0:
            raise ZeroDivisionError("Division by zero in mathematical expression.")
        return SAFE_OPERATORS[op_type](left, right)
    elif isinstance(node, ast.UnaryOp):
        op_type = type(node.op)
        if op_type not in SAFE_OPERATORS:
            raise ValueError(f"Unsupported unary operator: {op_type.__name__}")
        operand = _safe_eval(node.operand)
        return SAFE_OPERATORS[op_type](operand)
    elif isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name) or node.func.id not in SAFE_FUNCTIONS:
            raise ValueError(f"Disallowed or unsupported function: {ast.dump(node.func)}")
        func = SAFE_FUNCTIONS[node.func.id]
        args = [_safe_eval(arg) for arg in node.args]
        return func(*args)
    else:
        raise ValueError(f"Unsupported expression syntax: {type(node).__name__}")


def calculator(expression: str) -> str:
    """Safely evaluates a mathematical expression string.

    Supports arithmetic operations (+, -, *, /, //, %, **), parentheses,
    constants (pi, e), and standard functions (sqrt, abs, round, min, max, ceil, floor, log).

    Args:
        expression: The mathematical expression string (e.g., '(250 * 0.18) + (1500 / 12)').

    Returns:
        The calculated result as a string, or an error message if invalid.
    """
    cleaned = expression.strip()
    try:
        parsed = ast.parse(cleaned, mode="eval")
        result = _safe_eval(parsed)
        if isinstance(result, float) and result.is_integer():
            return str(int(result))
        return str(round(result, 6) if isinstance(result, float) else result)
    except Exception as exc:
        return f"Calculation error: {exc}"


# ---------------------------------------------------------------------------
# Knowledge Base Search
# ---------------------------------------------------------------------------

KNOWLEDGE_DOCUMENTS = [
    {
        "id": "KB-101",
        "title": "Cloud Architecture & Regional Clusters",
        "keywords": ["cluster", "region", "cloud", "latency", "zones", "infrastructure"],
        "content": (
            "Cluster-Alpha is deployed in us-central1 (Council Bluffs, Iowa) with 3 availability zones "
            "(us-central1-a, us-central1-b, us-central1-c). It currently hosts auth-service and web-gateway. "
            "Cluster-Beta is deployed in europe-west1 (St. Ghislain, Belgium) and hosts billing-api and data-pipeline. "
            "Inter-cluster latency between us-central1 and europe-west1 averages 105ms. "
            "Cross-region data transfer rate costs $0.02 per GB transferred."
        ),
    },
    {
        "id": "KB-102",
        "title": "On-Call Engineering Directory and Shift Schedule",
        "keywords": ["on-call", "engineer", "shift", "contact", "schedule", "escalation", "sre"],
        "content": (
            "Current On-Call Rotations (Shift: 08:00 - 20:00 UTC): "
            "1. auth-service: Alice Chen (Senior SRE, ID: ENG-401, email: alice.c@company.internal, shift ends 20:00 UTC). "
            "2. billing-api: Bob Martinez (Staff Backend Engineer, ID: ENG-402, email: bob.m@company.internal, shift ends 20:00 UTC). "
            "3. data-pipeline: Charlie Kim (Data Platform Engineer, ID: ENG-403, email: charlie.k@company.internal, shift ends 20:00 UTC). "
            "4. web-gateway: Diana Prince (Infrastructure SRE, ID: ENG-404, email: diana.p@company.internal, shift ends 20:00 UTC). "
            "Escalation Lead: Sarah Connor (Head of Infrastructure, ID: ENG-100)."
        ),
    },
    {
        "id": "KB-103",
        "title": "Service Level Objectives (SLOs) and Thresholds",
        "keywords": ["slo", "threshold", "limits", "latency", "error rate", "cpu", "memory", "alerts"],
        "content": (
            "Service Health Standard Thresholds: "
            "1. CPU Usage: Warning at >75%, Critical at >90%. "
            "2. Memory Usage: Warning at >80%, Critical at >90% (risk of OOM kill). "
            "3. Latency P99: auth-service SLO is <150ms; billing-api SLO is <250ms; web-gateway SLO is <80ms. "
            "4. Error Rate: Warning at >0.5%, Critical at >2.0% over a 5-minute rolling window. "
            "Any metric crossing Critical triggers an automated P1 incident ticket."
        ),
    },
    {
        "id": "KB-104",
        "title": "Compute Instance Types and Pricing",
        "keywords": ["instance", "pricing", "cost", "vm", "n2", "c3", "specs", "cpu", "ram"],
        "content": (
            "Compute VM Profiles: "
            "- n2-standard-4: 4 vCPUs, 16 GB RAM, $0.194 per hour ($139.68/mo based on 720h). "
            "- n2-standard-8: 8 vCPUs, 32 GB RAM, $0.388 per hour ($279.36/mo based on 720h). "
            "- c3-highcpu-8: 8 vCPUs, 16 GB RAM, high compute throughput, $0.342 per hour ($246.24/mo). "
            "- c3-highcpu-16: 16 vCPUs, 32 GB RAM, $0.684 per hour ($492.48/mo). "
            "Committed Use Discount (CUD): 1-year commitment offers 37% discount on all instances."
        ),
    },
    {
        "id": "KB-105",
        "title": "Quarterly Financial Performance (FY2025)",
        "keywords": ["revenue", "financial", "q1", "q2", "q3", "q4", "growth", "margin", "budget"],
        "content": (
            "FY2025 Cloud Platform Financial Highlights: "
            "- Q1 Revenue: $12.4M (Gross Margin: 72%). "
            "- Q2 Revenue: $14.1M (Gross Margin: 74%). "
            "- Q3 Revenue: $16.8M (Gross Margin: 76%). "
            "- Q4 Revenue: $19.5M (Gross Margin: 78%). "
            "Total annual revenue was $62.8M. Target annual growth rate was 25%; achieved growth rate was 31.2%."
        ),
    },
]


def search_knowledge_base(query: str) -> str:
    """Searches enterprise knowledge base for documentation, specs, architecture, or directory facts matching query keywords.

    Args:
        query: Search keywords or question phrase (e.g. 'on-call engineer auth-service', 'compute instance n2-standard-4 pricing').

    Returns:
        Matching documentation excerpts, or notice if no relevant articles were found.
    """
    terms = [t.lower().strip() for t in query.split() if len(t.strip()) > 2]
    if not terms:
        return "Search query was too short. Please provide specific keywords."

    scored_results: List[tuple[int, Dict[str, Any]]] = []
    for doc in KNOWLEDGE_DOCUMENTS:
        score = 0
        doc_text = (doc["title"] + " " + " ".join(doc["keywords"]) + " " + doc["content"]).lower()
        for term in terms:
            if term in doc_text:
                score += 2 if term in doc["title"].lower() else 1
        if score > 0:
            scored_results.append((score, doc))

    scored_results.sort(key=lambda x: x[0], reverse=True)

    if not scored_results:
        return f"No documentation found matching '{query}'. Try broader or alternative search keywords."

    output_lines = [f"Found {len(scored_results)} relevant document(s):"]
    for _, doc in scored_results[:3]:
        output_lines.append(f"[{doc['id']}] {doc['title']}:\n{doc['content']}")

    return "\n\n".join(output_lines)


# ---------------------------------------------------------------------------
# Real-Time Telemetry / System Metrics
# ---------------------------------------------------------------------------

LIVE_METRICS: Dict[str, Dict[str, Any]] = {
    "auth-service": {
        "status": "warning",
        "cluster": "cluster-alpha (us-central1)",
        "cpu_usage_pct": 68.4,
        "memory_usage_pct": 86.2,  # >80% warning
        "latency_p99_ms": 142.0,
        "requests_per_sec": 4250,
        "error_rate_pct": 0.12,
        "active_pod_count": 12,
        "max_pod_capacity": 20,
    },
    "billing-api": {
        "status": "healthy",
        "cluster": "cluster-beta (europe-west1)",
        "cpu_usage_pct": 42.1,
        "memory_usage_pct": 54.8,
        "latency_p99_ms": 118.5,
        "requests_per_sec": 1120,
        "error_rate_pct": 0.04,
        "active_pod_count": 6,
        "max_pod_capacity": 15,
    },
    "data-pipeline": {
        "status": "healthy",
        "cluster": "cluster-beta (europe-west1)",
        "cpu_usage_pct": 81.3,
        "memory_usage_pct": 72.0,
        "latency_p99_ms": 310.0,
        "requests_per_sec": 840,
        "error_rate_pct": 0.08,
        "active_pod_count": 8,
        "max_pod_capacity": 16,
    },
    "web-gateway": {
        "status": "healthy",
        "cluster": "cluster-alpha (us-central1)",
        "cpu_usage_pct": 55.0,
        "memory_usage_pct": 61.3,
        "latency_p99_ms": 48.2,
        "requests_per_sec": 9800,
        "error_rate_pct": 0.02,
        "active_pod_count": 18,
        "max_pod_capacity": 30,
    },
}


def system_metrics_query(service_name: str, metric: Optional[str] = None) -> str:
    """Queries live telemetry metrics for microservices and cloud workloads.

    Args:
        service_name: Name of the service ('auth-service', 'billing-api', 'data-pipeline', 'web-gateway').
        metric: Optional specific metric ('cpu_usage_pct', 'memory_usage_pct', 'latency_p99_ms',
                'requests_per_sec', 'error_rate_pct', 'active_pod_count'). If omitted, returns all metrics.

    Returns:
        Telemetry values or status summary.
    """
    svc = service_name.strip().lower()
    if svc not in LIVE_METRICS:
        available = ", ".join(LIVE_METRICS.keys())
        return f"Service '{service_name}' not found. Available services: {available}"

    svc_data = LIVE_METRICS[svc]
    if metric:
        met = metric.strip().lower()
        if met in svc_data:
            return f"{svc} {met}: {svc_data[met]}"
        valid_metrics = ", ".join(svc_data.keys())
        return f"Metric '{metric}' not recognized for {svc}. Valid metrics: {valid_metrics}"

    lines = [f"Metrics for service: {svc} (Cluster: {svc_data['cluster']}, Status: {svc_data['status'].upper()})"]
    for k, v in svc_data.items():
        if k not in ("cluster", "status"):
            lines.append(f"  - {k}: {v}")
    return "\n".join(lines)



# ---------------------------------------------------------------------------
# Structured Database Lookup
# ---------------------------------------------------------------------------

DATABASE_RECORDS: Dict[str, Dict[str, Dict[str, Any]]] = {
    "incidents": {
        "INC-101": {
            "title": "High Memory Utilization on auth-service",
            "service": "auth-service",
            "severity": "P2-Warning",
            "created_at": "2025-11-27 10:15 UTC",
            "status": "investigating",
            "assignee": "Alice Chen",
            "summary": "auth-service memory crossed 85% threshold due to redis connection pool leak.",
        },
        "INC-102": {
            "title": "Payment Webhook Timeout",
            "service": "billing-api",
            "severity": "P3-Minor",
            "created_at": "2025-11-26 14:30 UTC",
            "status": "resolved",
            "assignee": "Bob Martinez",
            "summary": "External gateway timeout during batch invoicing; resolved after retry policy update.",
        },
        "INC-103": {
            "title": "Data Pipeline Backpressure in Europe",
            "service": "data-pipeline",
            "severity": "P3-Minor",
            "created_at": "2025-11-25 09:00 UTC",
            "status": "mitigated",
            "assignee": "Charlie Kim",
            "summary": "Kafka topic consumer lag accumulated; auto-scaled consumers to clear queue.",
        },
    },
    "servers": {
        "srv-prod-01": {
            "hostname": "srv-prod-01.us-central1.company.internal",
            "cluster": "cluster-alpha",
            "instance_type": "n2-standard-8",
            "ip": "10.128.0.24",
            "uptime_days": 142,
            "maintenance_window": "Sunday 02:00 UTC",
        },
        "srv-prod-02": {
            "hostname": "srv-prod-02.europe-west1.company.internal",
            "cluster": "cluster-beta",
            "instance_type": "c3-highcpu-16",
            "ip": "10.132.0.18",
            "uptime_days": 89,
            "maintenance_window": "Saturday 03:00 UTC",
        },
    },
}


def database_lookup(table: str, record_id: str) -> str:
    """Retrieves a specific record from structured database tables (e.g. incidents, servers).

    Args:
        table: Table name ('incidents', 'servers').
        record_id: Record key (e.g. 'INC-101', 'INC-102', 'srv-prod-01', 'srv-prod-02').

    Returns:
        Structured record details or error message if not found.
    """
    tbl = table.strip().lower()
    rec_id = record_id.strip()

    if tbl not in DATABASE_RECORDS:
        available_tables = ", ".join(DATABASE_RECORDS.keys())
        return f"Table '{table}' does not exist. Available tables: {available_tables}"

    table_data = DATABASE_RECORDS[tbl]
    match = table_data.get(rec_id)
    if not match:
        for k, v in table_data.items():
            if k.lower() == rec_id.lower():
                match = v
                rec_id = k
                break

    if not match:
        keys = ", ".join(table_data.keys())
        return f"Record '{record_id}' not found in table '{table}'. Available records: {keys}"

    lines = [f"Record [{rec_id}] in table '{table}':"]
    for k, v in match.items():
        lines.append(f"  - {k}: {v}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# ADK FunctionTool Wrappers
# ---------------------------------------------------------------------------

calculator_tool = FunctionTool(calculator)
search_tool = FunctionTool(search_knowledge_base)
metrics_tool = FunctionTool(system_metrics_query)
database_tool = FunctionTool(database_lookup)

ALL_REACT_TOOLS = [
    search_tool,
    calculator_tool,
    metrics_tool,
    database_tool,
]

