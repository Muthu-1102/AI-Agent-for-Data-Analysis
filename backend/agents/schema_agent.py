import pandas as pd
from typing import Dict, Any

from core.pipeline import PipelineStep, step_logging_wrapper
from models.schema_model import DataSchema, ColumnInfo
from utils.helpers import load_and_clean_dataset, resolve_dataset_path


class SchemaAgent(PipelineStep):
    """
    Data Engineering Agent responsible for introspecting a dataset.
    Extracts structural metadata (schema) to inform downstream code-generation LLMs,
    ensuring they write Pandas code tailored precisely to the data's shape and types.

    Returns a validated DataSchema model object stored under state['schema_info'].
    """

    @step_logging_wrapper
    async def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parses the dataset (CSV) and returns a validated DataSchema instance.
        """
        file_id = state.get("file_id")
        if not file_id:
            raise ValueError("SchemaAgent requires a valid 'file_id' in the state context.")

        try:
            # Use the centralised helper to resolve the actual path on disk
            file_path = resolve_dataset_path(file_id)
            df = load_and_clean_dataset(file_id, nrows=1000)

            # Build per-column detail objects
            column_details = [
                ColumnInfo(
                    name=col,
                    dtype=str(df[col].dtype),
                    null_count=int(df[col].isnull().sum()),
                    sample_values=df[col].dropna().head(3).tolist(),
                )
                for col in df.columns
            ]

            # Construct and validate the full schema via the Pydantic model
            schema = DataSchema(
                columns=list(df.columns),
                dtypes={col: str(dtype) for col, dtype in df.dtypes.items()},
                null_counts=df.isnull().sum().to_dict(),
                row_count=len(df),
                sample_rows=df.head(5).to_dict(orient="records"),
                column_details=column_details,
            )

            return {"schema_info": schema.model_dump()}

        except FileNotFoundError:
            raise RuntimeError(f"Data file could not be found: {file_id}")
        except Exception as e:
            raise RuntimeError(f"SchemaAgent failed to extract schema for '{file_id}': {str(e)}")
