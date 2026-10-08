import sqlglot
from sqlglot import exp

from backend.contracts import Learning, ResultTable
from backend.security.gateway import ValidatedQuery
from backend.semantic.catalog import GRAINS


def explain(query: ValidatedQuery, exercise_id: str | None = None) -> Learning:
    tree = sqlglot.parse_one(query.display_sql, read="tsql")
    concepts = ["SELECT", "Table grain"]
    explanations = [
        "Logical processing begins with FROM/JOIN, then WHERE, GROUP BY, HAVING, "
        "SELECT/window calculations, ORDER BY and TOP. The optimizer may execute differently."
    ]
    lessons = [
        (
            exp.Join,
            "JOIN",
            "The approved join preserves job grain: each job matches at most one customer, "
            "or one invoice ranked by ROW_NUMBER per JobId with rank = 1 in ON. "
            "LEFT JOIN keeps unmatched jobs with NULL values on the right.",
        ),
        (exp.Where, "WHERE", "WHERE filters input rows before aggregation."),
        (exp.Group, "GROUP BY", "GROUP BY produces one row per combination of grouping values."),
        (exp.Having, "HAVING", "HAVING filters aggregated groups; WHERE filters individual rows."),
        (
            exp.CTE,
            "CTE",
            "A CTE names an intermediate query. It does not automatically materialize "
            "results or make a many-to-many join safe.",
        ),
        (
            exp.Subquery,
            "Subquery",
            "The uncorrelated subquery computes an independent scalar or relation used by the outer SELECT.",
        ),
        (
            exp.Window,
            "Window function",
            "A window function computes across a partition while "
            "preserving rows. Include a deterministic ordering for rankings.",
        ),
        (exp.Nullif, "NULLIF", "NULLIF makes a zero denominator NULL, avoiding division by zero."),
        (
            exp.Limit,
            "TOP",
            "TOP is part of this explicit query; the gateway never inserts it. "
            "ORDER BY determines which rows qualify.",
        ),
    ]
    for node_type, name, text in lessons:
        if tree.find(node_type):
            concepts.append(name)
            explanations.append(text)
    if tree.find(exp.AggFunc):
        concepts.append("Aggregation")
        explanations.append(
            "Aggregates operate at the input grain. Margin percentage is a ratio "
            "of totals, not an average of job percentages."
        )
    return Learning(
        grain="; ".join(f"{name}: {GRAINS[name]}" for name in query.views),
        concepts=concepts,
        explanation=explanations,
        cautions=[
            "Joining invoice and expense detail multiplies amounts; pre-aggregate each fact by JobId.",
            "Budget variance = budget minus expenses; positive is favorable. Currency is CAD.",
            "Avoid functions on indexed filter columns when a date range can express the filter.",
            "Valid and authorized SQL can still answer the wrong business question; inspect grain "
            "and filters. Practice uses an independent reference, not the generated proposal.",
        ],
        exercise_id=exercise_id,
    )


def grounded_answer(result: ResultTable) -> str:
    """A deterministic narrative cannot invent claims or execute instructions in returned cells."""
    if not result.rows:
        return "The query returned no matching rows. Review the filters before drawing conclusions."
    if len(result.rows) == 1:
        facts = "; ".join(
            f"{name}: {value if value is not None else 'not defined'}"
            for name, value in zip(result.columns, result.rows[0], strict=True)
        )
        return "Verified query result — " + facts + ". Financial amounts use CAD."
    return (
        f"The query returned {result.row_count} rows with {', '.join(result.columns)}. "
        "The complete bounded result is shown below; financial amounts use CAD."
    )
