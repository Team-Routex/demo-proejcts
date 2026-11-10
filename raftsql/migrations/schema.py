"""Get table schema (name + columns with types) from Model for migrations."""
from typing import Dict, List, Tuple, Type

from ..db.backends.base import Backend
from ..orm.model import Model, column_names, pk_column, table_name


# ── Model-state snapshot ──────────────────────────────────────────────────────
# The snapshot format stored in migration files under ``model_state``:
#
#   model_state = {
#       "blogs": {                    # table name
#           "fields": {
#               "id":    {"field_class": "AutoField",  "col": "id",    "sql": "SERIAL PRIMARY KEY"},
#               "title": {"field_class": "CharField",  "col": "title", "sql": "VARCHAR(255) NOT NULL"},
#           }
#       }
#   }
#
# ``field_class`` is the Python class name (e.g. "CharField").
# ``col``         is the DB column name (may differ for ForeignKey: author -> author_id).
# ``sql``         is the full column SQL (used to rebuild the legacy SQL-based state).

def snapshot_from_model(model_class: Type[Model]) -> dict:
    """
    Return a dict describing the model's field structure for storage in a
    migration file's ``model_state``.

    Only scalar/FK fields are included (no M2M — those have their own tables).
    Constraints from ``class Meta: constraints = [...]`` are stored under the
    ``"constraints"`` key so they survive round-trips through model_state.
    """
    from ..orm.fields import Field, ManyToManyField
    from ..orm.model import _get_column_name  # type: ignore[attr-defined]

    t = table_name(model_class)
    field_types = getattr(model_class, "_field_types", {}) or {}
    fields_meta: Dict[str, dict] = {}

    for attr_name, value in vars(model_class).items():
        if attr_name.startswith("_") or attr_name == "Meta":
            continue
        if not isinstance(value, Field):
            continue
        if isinstance(value, ManyToManyField):
            continue  # separate junction table snapshot

        col = _get_column_name(attr_name, value)
        sql = field_types.get(col, value.get_column_sql() if hasattr(value, "get_column_sql") else "TEXT")
        fields_meta[attr_name] = {
            "field_class": type(value).__name__,
            "col": col,
            "sql": sql,
        }

    # Capture Meta.constraints so they are preserved in model_state and don't
    # get re-generated as AddConstraint on every subsequent makemigrations run.
    constraints_meta: Dict[str, str] = {}
    for c in getattr(model_class, "_constraints", []):
        constraints_meta[c.name] = c.as_sql(None)

    table_entry: dict = {"fields": fields_meta}
    if constraints_meta:
        table_entry["constraints"] = constraints_meta

    return {t: table_entry}


def snapshot_from_models(models: list) -> dict:
    """Return combined model_state snapshot for a list of Model classes."""
    result: dict = {}
    for model in models:
        result.update(snapshot_from_model(model))
    return result


def field_signature(field_meta: dict) -> str:
    """
    Return a string that uniquely identifies a field's *type* (not its name).
    Used to detect renames: if the signature matches, the field is a rename candidate.
    """
    return f"{field_meta['field_class']}:{field_meta['sql']}"


def get_schema_from_model(model_class: Type[Model], backend: Backend) -> Tuple[str, List[Tuple[str, str]]]:
    """
    Return (table_name, [(column_name, type_sql), ...]) for a Model's own table.
    Constraint entries use "__c__{name}" as the column key and the full CONSTRAINT SQL as value.
    ManyToManyField columns are NOT included here — they produce separate junction tables.
    """
    table = table_name(model_class)
    cols = column_names(model_class)
    pk_col = pk_column(model_class)
    field_types = getattr(model_class, "_field_types", None) or {}
    default_pk = "SERIAL PRIMARY KEY"
    default_other = "TEXT"
    columns: List[Tuple[str, str]] = []
    for c in cols:
        if c in field_types:
            columns.append((c, field_types[c]))
        else:
            columns.append((c, default_pk if c == pk_col else default_other))

    # Append Meta.constraints as special sentinel entries understood by the backend
    for constraint in getattr(model_class, "_constraints", []):
        sql = constraint.as_sql(backend)
        columns.append((f"__c__{constraint.name}", sql))

    return table, columns


def get_m2m_schemas(model_class: Type[Model]) -> List[Tuple[str, List[Tuple[str, str]]]]:
    """
    Return a list of (junction_table_name, columns) for every ManyToManyField on the model.
    Skips fields that use an explicit through Model class (those have their own migrations).
    """
    m2m_fields = getattr(model_class, "_m2m", {})
    src_table = table_name(model_class)
    result = []
    for _attr_name, m2m_field in m2m_fields.items():
        # Skip explicit through Model classes — they manage their own table
        through = m2m_field.through
        if through is not None and not isinstance(through, str):
            continue
        to_model = m2m_field.to
        dst_table = table_name(to_model)
        junction = m2m_field.get_junction_table(src_table, dst_table)
        src_col = f"{src_table}_id"
        dst_col = f"{dst_table}_id"
        columns: List[Tuple[str, str]] = [
            ("id", "SERIAL PRIMARY KEY"),
            (src_col, "INTEGER NOT NULL"),
            (dst_col, "INTEGER NOT NULL"),
        ]
        result.append((junction, columns))
    return result
