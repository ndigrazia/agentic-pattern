"""Unit tests for ReAct tools (calculator, search, telemetry metrics, database)."""

from pathlib import Path
import sys
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from google.adk.tools import FunctionTool
from react_agent.tools import (
    ALL_REACT_TOOLS,
    calculator,
    calculator_tool,
    database_lookup,
    database_tool,
    metrics_tool,
    search_knowledge_base,
    search_tool,
    system_metrics_query,
)


class TestCalculator:
    def test_basic_arithmetic(self):
        assert calculator("2 + 2") == "4"
        assert calculator("10 - 4") == "6"
        assert calculator("6 * 7") == "42"
        assert calculator("100 / 4") == "25"

    def test_complex_expressions(self):
        expr = "((19.5 - 16.8) / 16.8) * 100"
        res = float(calculator(expr))
        assert round(res, 2) == 16.07

    def test_math_functions(self):
        assert calculator("sqrt(144)") == "12"
        assert calculator("round(3.14159, 2)") == "3.14"
        assert calculator("max(10, 20, 5)") == "20"

    def test_division_by_zero(self):
        res = calculator("10 / 0")
        assert "Calculation error" in res
        assert "division by zero" in res.lower()

    def test_unsupported_syntax(self):
        res = calculator("__import__('os').system('ls')")
        assert "Calculation error" in res


class TestSearchKnowledgeBase:
    def test_search_cloud_clusters(self):
        res = search_knowledge_base("cluster-alpha region")
        assert "Cluster-Alpha" in res
        assert "us-central1" in res

    def test_search_on_call(self):
        res = search_knowledge_base("on-call auth-service engineer")
        assert "Alice Chen" in res
        assert "ENG-401" in res

    def test_search_no_results(self):
        res = search_knowledge_base("supercalifragilisticexpialidocious")
        assert "No documentation found" in res

    def test_short_query(self):
        res = search_knowledge_base("a")
        assert "too short" in res.lower()


class TestSystemMetricsQuery:
    def test_query_all_metrics(self):
        res = system_metrics_query("auth-service")
        assert "auth-service" in res
        assert "memory_usage_pct" in res
        assert "cpu_usage_pct" in res

    def test_query_single_metric(self):
        res = system_metrics_query("auth-service", "memory_usage_pct")
        assert "86.2" in res

    def test_query_unknown_service(self):
        res = system_metrics_query("non-existent-service")
        assert "not found" in res.lower()

    def test_query_unknown_metric(self):
        res = system_metrics_query("billing-api", "invalid_metric")
        assert "not recognized" in res.lower()


class TestDatabaseLookup:
    def test_lookup_incident(self):
        res = database_lookup("incidents", "INC-101")
        assert "High Memory Utilization" in res
        assert "Alice Chen" in res

    def test_lookup_server(self):
        res = database_lookup("servers", "srv-prod-01")
        assert "srv-prod-01" in res
        assert "n2-standard-8" in res

    def test_unknown_table(self):
        res = database_lookup("customers", "CUST-1")
        assert "does not exist" in res.lower()

    def test_unknown_record(self):
        res = database_lookup("incidents", "INC-999")
        assert "not found" in res.lower()


class TestToolWrappers:
    def test_tool_instances(self):
        assert len(ALL_REACT_TOOLS) == 4
        for tool in ALL_REACT_TOOLS:
            assert isinstance(tool, FunctionTool)
            assert tool.name in (
                "search_knowledge_base",
                "calculator",
                "system_metrics_query",
                "database_lookup",
            )
