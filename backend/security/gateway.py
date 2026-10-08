"""Positive SQL grammar policy, scope-aware authorization and parameter compilation."""

import logging
import math
import re
from dataclasses import dataclass
from typing import Any

import sqlglot
from sqlglot import exp
from sqlglot.dialects.tsql import TSQL
from sqlglot.errors import OptimizeError, ParseError, SqlglotError
from sqlglot.optimizer.qualify import qualify
from sqlglot.optimizer.scope import Scope, traverse_scope

from backend.contracts import Parameter, Scalar
from backend.semantic.catalog import VIEWS

# Parser fallback diagnostics can contain raw SQL/user literals. Application errors are sanitized.
logging.getLogger("sqlglot").setLevel(logging.CRITICAL)


class PolicyError(ValueError):
    """A proposal is outside the reviewed query language."""


# New SQLGlot nodes are denied until reviewed. Pinning the parser is intentional.
ALLOWED_NODES = frozenset(
    {
        "Select",
        "Alias",
        "Column",
        "Identifier",
        "Table",
        "TableAlias",
        "From",
        "Join",
        "Where",
        "Group",
        "Having",
        "Order",
        "Ordered",
        "Limit",
        "Literal",
        "Star",
        "And",
        "Or",
        "Not",
        "EQ",
        "NEQ",
        "GT",
        "GTE",
        "LT",
        "LTE",
        "In",
        "Between",
        "Is",
        "Null",
        "Boolean",
        "Paren",
        "Add",
        "Sub",
        "Mul",
        "Div",
        "Neg",
        "Mod",
        "Sum",
        "Avg",
        "Count",
        "Min",
        "Max",
        "Round",
        "Coalesce",
        "Nullif",
        "Abs",
        "Cast",
        "DataType",
        "DataTypeParam",
        "Distinct",
        "With",
        "CTE",
        "Subquery",
        "Window",
        "WindowSpec",
        "RowNumber",
        "Rank",
        "DenseRank",
        "Lag",
        "Lead",
        "LimitOptions",
        "Case",
        "If",
        "Year",
        "Month",
        "Extract",
        "Var",
        "Parameter",
    }
)


@dataclass(frozen=True)
class ValidatedQuery:
    display_sql: str
    bound_sql: str
    values: tuple[Scalar, ...]
    views: tuple[str, ...]


class SQLGateway:
    def validate(self, sql: str, parameters: list[Parameter] | None = None) -> ValidatedQuery:
        if not sql.strip() or len(sql) > 12000:
            raise PolicyError("SQL must contain 1–12,000 characters")
        # Comments, control characters and alternate batches are outside the supported language.
        if re.search(r"--|/\*|\*/|[\x00-\x08\x0b\x0c\x0e-\x1f]", sql):
            raise PolicyError("Comments and control characters are not supported")
        try:
            statements = sqlglot.parse(sql, read="tsql", error_level=sqlglot.ErrorLevel.RAISE)
            if len(statements) != 1 or not isinstance(statements[0], exp.Select):
                raise PolicyError("Only one SELECT or nonrecursive SELECT CTE is supported")
            tree = statements[0]
            nodes = list(tree.walk())
            if len(nodes) > 400 or len(list(tree.find_all(exp.Select))) > 8:
                raise PolicyError("Query complexity limit exceeded")
            for node in nodes:
                if type(node).__name__ not in ALLOWED_NODES:
                    raise PolicyError(f"Unsupported SQL construct: {type(node).__name__}")
                if isinstance(node, exp.Identifier) and not re.fullmatch(
                    r"[A-Za-z_][A-Za-z0-9_]{0,63}", node.name
                ):
                    raise PolicyError("Unsupported identifier")
                if isinstance(node, exp.Star) and not isinstance(node.parent, exp.Count):
                    raise PolicyError("List columns explicitly; only COUNT(*) permits a wildcard")
                if isinstance(node, exp.With) and node.args.get("recursive"):
                    raise PolicyError("Recursive CTEs are prohibited")
                if isinstance(node, exp.Var):
                    if isinstance(node.parent, exp.Parameter):
                        if not re.fullmatch(r"[a-z][a-z0-9_]{0,31}", node.name):
                            raise PolicyError("Invalid parameter name")
                    elif not (
                        isinstance(node.parent, exp.Extract) and node.name.upper() in {"YEAR", "MONTH", "DAY"}
                    ):
                        raise PolicyError("Unsupported variable or date part")
                if isinstance(node, exp.Limit):
                    value = node.expression
                    if not isinstance(value, exp.Literal) or not value.is_int:
                        raise PolicyError("TOP must be a constant integer")
                    options = node.args.get("limit_options")
                    if not 1 <= int(value.this) <= 2000 or (options and any(options.args.values())):
                        raise PolicyError("TOP must be 1–2000 without PERCENT or WITH TIES")
            views = self._authorize_sources(tree)
            tree = qualify(tree, dialect="tsql", schema={"reporting": VIEWS})
            self._authorize_joins(tree)
            bindings = parameters or []
            values_by_name = {item.name: item.value for item in bindings}
            if len(values_by_name) != len(bindings) or len(bindings) > 20:
                raise PolicyError("Duplicate or excess parameters")
            used = {node.name for node in tree.find_all(exp.Parameter)}
            if used != set(values_by_name):
                raise PolicyError("SQL parameters and supplied values must match exactly")
            for value in values_by_name.values():
                if isinstance(value, str) and len(value) > 1000:
                    raise PolicyError("Parameter value too long")
                if isinstance(value, float) and not math.isfinite(value):
                    raise PolicyError("Non-finite parameter")
                if isinstance(value, int) and not -(2**63) <= value < 2**63:
                    raise PolicyError("Integer parameter outside SQL bigint range")
            display = tree.sql(dialect="tsql", pretty=True)
            # Bind AST parameter nodes in SQL rendering order, never by editing SQL strings.
            ordered: list[Scalar] = []

            def bind(generator: Any, node: Any) -> str:
                ordered.append(values_by_name[node.name])
                return "?"

            generator = TSQL.Generator()
            generator.TRANSFORMS = {**generator.TRANSFORMS, exp.Parameter: bind}
            bound = generator.generate(tree)
            return ValidatedQuery(display, bound, tuple(ordered), tuple(sorted(views)))
        except PolicyError:
            raise
        except (ParseError, OptimizeError, SqlglotError, ValueError, RecursionError) as exc:
            raise PolicyError("Invalid, ambiguous or unauthorized T-SQL") from exc

    @staticmethod
    def _authorize_sources(tree: Any) -> set[str]:
        approved = {name.lower(): name for name in VIEWS}
        views: set[str] = set()
        for scope in traverse_scope(tree):
            for _, source in scope.sources.items():
                if isinstance(source, exp.Table):
                    if (
                        source.catalog
                        or source.db.lower() != "reporting"
                        or source.name.lower() not in approved
                        or not isinstance(source.this, exp.Identifier)
                    ):
                        raise PolicyError("Only explicitly approved reporting views are authorized")
                    views.add(approved[source.name.lower()])
                elif not isinstance(source, Scope):
                    raise PolicyError("Unsupported data source")
        if not views:
            raise PolicyError("A query must read an approved reporting view")
        return views

    @staticmethod
    def _authorize_joins(tree: Any) -> None:
        for scope in traverse_scope(tree):
            if scope.is_correlated_subquery:
                raise PolicyError("Correlated subqueries are not supported")
            joins = scope.expression.args.get("joins") or []
            if not joins:
                continue
            if len(joins) != 1 or len(scope.selected_sources) != 2:
                raise PolicyError("Only one approved join preserving the job grain is supported")
            sources = {alias: source for alias, (_, source) in scope.selected_sources.items()}
            if SQLGateway._ranked_invoice_join(scope, sources, joins[0]):
                continue
            if any(not isinstance(source, exp.Table) for source in sources.values()):
                raise PolicyError("Joins to CTEs or derived tables require separate semantic review")
            names = {alias: source.name.lower() for alias, source in sources.items()}
            from_table = scope.expression.args["from"].this
            join = joins[0]
            if (
                names.get(from_table.alias_or_name) not in {"vjobs", "vjobfinancials"}
                or names.get(join.this.alias_or_name) != "vcustomers"
                or join.args.get("side", "").upper() not in {"", "LEFT"}
                or join.args.get("kind", "").upper() not in {"", "INNER"}
            ):
                raise PolicyError("Join direction or tables could multiply the metric grain")
            on = join.args.get("on")
            if not isinstance(on, exp.EQ) or not all(
                isinstance(node, exp.Column) and node.name.lower() == "customerid"
                for node in (on.left, on.right)
            ):
                raise PolicyError("Approved joins require equality on CustomerId")
            if {on.left.table, on.right.table} != set(sources):
                raise PolicyError("Join must connect both sources by their approved key")

    @staticmethod
    def _ranked_invoice_join(scope: Any, sources: dict[str, Any], join: Any) -> bool:
        """Prove at most one invoice per job: passthrough JobId + ROW_NUMBER partition + rank=1.

        This is deliberately narrower than arbitrary joins to CTEs. RANK/DENSE_RANK,
        changed keys, OR predicates and missing rank filters do not establish this property.
        """
        left_alias = scope.expression.args["from"].this.alias_or_name
        right_alias = join.this.alias_or_name
        left, right = sources.get(left_alias), sources.get(right_alias)
        if not (
            isinstance(left, exp.Table)
            and left.name.lower() in {"vjobs", "vjobfinancials"}
            and isinstance(right, Scope)
            and join.args.get("side", "").upper() in {"", "LEFT"}
            and join.args.get("kind", "").upper() in {"", "INNER"}
        ):
            return False
        select = right.expression
        inputs = list(right.selected_sources.items())
        if len(inputs) != 1 or not isinstance(select, exp.Select):
            return False
        invoice_alias, (_, invoice) = inputs[0]
        if not isinstance(invoice, exp.Table) or invoice.name.lower() != "vinvoices":
            return False
        if any(select.args.get(key) for key in ("joins", "group", "having", "distinct", "limit")):
            return False
        job_key = False
        rank_alias: str | None = None
        output_names: set[str] = set()
        for projection in select.expressions:
            name = projection.alias_or_name.lower()
            if name in output_names:
                return False
            output_names.add(name)
            value = projection.this if isinstance(projection, exp.Alias) else projection
            if isinstance(value, exp.Column) and value.table == invoice_alias:
                if name == "jobid":
                    job_key = value.name.lower() == "jobid"
                    if not job_key:
                        return False
            elif isinstance(value, exp.Window) and isinstance(value.this, exp.RowNumber):
                partition = value.args.get("partition_by") or []
                order = value.args.get("order")
                if (
                    rank_alias is not None
                    or name == "jobid"
                    or len(partition) != 1
                    or not isinstance(partition[0], exp.Column)
                    or partition[0].table != invoice_alias
                    or partition[0].name.lower() != "jobid"
                    or order is None
                    or not any(
                        isinstance(item.this, exp.Column)
                        and item.this.table == invoice_alias
                        and item.this.name.lower() == "invoiceid"
                        for item in order.expressions
                    )
                ):
                    return False
                rank_alias = name
            else:
                return False
        if not job_key or rank_alias is None:
            return False

        def is_column(node: Any, alias: str, name: str) -> bool:
            return isinstance(node, exp.Column) and node.table == alias and node.name.lower() == name

        on = join.args.get("on")

        def conjunctions(node: Any) -> list[Any]:
            node = node.unnest()
            if isinstance(node, exp.And):
                return conjunctions(node.left) + conjunctions(node.right)
            return [node]

        predicates = conjunctions(on) if on is not None else []
        if len(predicates) != 2 or not all(isinstance(item, exp.EQ) for item in predicates):
            return False
        key_match = rank_match = False
        for predicate in predicates:
            for a, b in ((predicate.left, predicate.right), (predicate.right, predicate.left)):
                key_match |= is_column(a, left_alias, "jobid") and is_column(b, right_alias, "jobid")
                rank_match |= (
                    is_column(a, right_alias, rank_alias)
                    and isinstance(b, exp.Literal)
                    and b.is_int
                    and b.this == "1"
                )
        return key_match and rank_match
