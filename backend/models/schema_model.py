from pydantic import BaseModel, Field, model_validator
from typing import List, Dict, Any, Optional


class ColumnInfo(BaseModel):
    """
    Detailed metadata for a single dataset column.
    """
    name: str = Field(..., description="Original column name as it appears in the CSV header.")
    dtype: str = Field(..., description="Inferred Pandas data type string (e.g. 'int64', 'float64', 'object', 'datetime64').")
    null_count: int = Field(default=0, description="Number of missing / null values in this column.")
    sample_values: List[Any] = Field(default_factory=list, description="Up to 3 representative sample values from this column.")


class DataSchema(BaseModel):
    """
    Pydantic model representing the fully structured metadata extracted from a dataset
    by the SchemaAgent.

    Responsibilities:
    - Validates all schema fields at the boundary between SchemaAgent output and
      PromptAgent / CodeAgent input.
    - Provides a single source of truth for dataset structure used downstream by
      every LLM-facing agent.
    - Ensures JSON-serialisable, type-safe data flows through the pipeline state dict.
    """

    # ── Core Shape ─────────────────────────────────────────────────────────────
    columns: List[str] = Field(
        ...,
        description="Ordered list of column names exactly as they appear in the dataset header."
    )
    dtypes: Dict[str, str] = Field(
        ...,
        description="Mapping of column name → Pandas dtype string."
    )
    null_counts: Dict[str, int] = Field(
        ...,
        description="Mapping of column name → count of null/NaN values."
    )

    # ── Shape Metadata ──────────────────────────────────────────────────────────
    row_count: Optional[int] = Field(
        default=None,
        description="Total number of rows in the dataset (may be an estimate for large files)."
    )
    column_count: Optional[int] = Field(
        default=None,
        description="Total number of columns. Auto-derived from 'columns' if not supplied."
    )

    # ── LLM Context ─────────────────────────────────────────────────────────────
    sample_rows: List[Dict[str, Any]] = Field(
        ...,
        description="3–5 representative rows as a list of dicts, giving the LLM visual data formatting context."
    )
    column_details: Optional[List[ColumnInfo]] = Field(
        default=None,
        description="Optional per-column detail objects. Populated by SchemaAgent when available."
    )

    # ── Derived fields validator ────────────────────────────────────────────────
    @model_validator(mode="after")
    def derive_column_count(self) -> "DataSchema":
        """Auto-fills column_count from the columns list when not explicitly set."""
        if self.column_count is None:
            self.column_count = len(self.columns)
        return self

    # ── Convenience helpers ─────────────────────────────────────────────────────
    def to_llm_summary(self) -> str:
        """
        Serialises the schema into a compact, human-readable string optimised for
        injection into LLM system prompts. Keeps token usage minimal.

        Example output:
            Dataset Shape: 1024 rows × 8 columns
            Columns:
              - order_id (int64, 0 nulls)
              - product_name (object, 3 nulls)
              ...
            Sample rows:
              [{'order_id': 1, 'product_name': 'Widget A', ...}, ...]
        """
        lines = []

        shape = f"{self.row_count or '?'} rows × {self.column_count} columns"
        lines.append(f"Dataset Shape: {shape}")

        lines.append("Columns:")
        for col in self.columns:
            dtype = self.dtypes.get(col, "unknown")
            nulls = self.null_counts.get(col, 0)
            lines.append(f"  - {col} ({dtype}, {nulls} nulls)")

        lines.append(f"Sample rows:\n  {self.sample_rows[:3]}")

        return "\n".join(lines)
