from typing import Dict, Any

from core.pipeline import PipelineStep, step_logging_wrapper
from models.schema_model import DataSchema


class PromptAgent(PipelineStep):
    """
    Prompt Engineer Agent responsible for enhancing the user's query.
    It takes the raw user query and the extracted dataset schema, and constructs
    a highly structured, comprehensive prompt that is optimized for the Code Agent.
    """

    @step_logging_wrapper
    async def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Constructs the structured prompt using the DataSchema summary and the user query.
        """
        # Key is 'query' as set by the Orchestrator
        user_query = state.get("query")
        schema_info = state.get("schema_info")

        if not user_query:
            raise ValueError("PromptAgent requires 'query' in the state context.")
        if not schema_info:
            raise ValueError("PromptAgent requires 'schema_info' in the state context.")

        # Re-hydrate the validated Pydantic model from the serialised state dict
        schema = DataSchema(**schema_info)

        # Use the model's built-in helper for a compact, token-efficient summary
        schema_context = schema.to_llm_summary()

        structured_prompt = f"""You are an elite Data Scientist and expert Python Pandas developer.
Your task is to write a precise, efficient Python script to analyze a dataset to fulfill the user's request.

=== DATASET CONTEXT ===
The dataset has already been loaded into a Pandas DataFrame named `df`.
Here is the schema and sample data for `df`:

{schema_context}

=== USER REQUEST ===
{user_query}

=== IMPLEMENTATION INSTRUCTIONS ===
1. Write complete, executable Python code using the `pandas` library.
2. The DataFrame `df` is globally available. Do NOT write code to load the CSV file.
3. Do NOT import `os`, `sys`, `subprocess`, `shutil`, or any standard library modules.
4. Focus strictly on answering the USER REQUEST.
5. Prefer textual results: only generate charts or plots if the user explicitly asks for visualizations, the question refers to trends/patterns best shown visually, or a chart is necessary to answer the request clearly.
6. If generating visual charts or plots, use `matplotlib.pyplot` or `seaborn`. Save the plot to 'output_plot.png' using plt.savefig('output_plot.png').
7. Always print the key findings or chart summary to standard output with `print()`, even when a chart is generated.
8. Do NOT provide explanations. Output ONLY valid, executable Python code.

# YOUR PYTHON CODE:
"""

        return {
            "structured_prompt": structured_prompt
        }
