from typing import Dict, Any

from core.pipeline import PipelineStep, step_logging_wrapper
from config import settings
from services.llm_service import LLMService

class ReportAgent(PipelineStep):
    """
    Data Analyst Agent responsible for interpreting execution results and
    generating a final human-readable insights summary.
    """
    
    def __init__(self):
        # Delegate LLM interactions to the standardized service
        self.llm_service = LLMService(
            api_key=settings.GROQ_API_KEY,
            default_model=settings.GROQ_MODEL
        )
        
    @step_logging_wrapper
    async def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Takes raw console stdout from the ExecutionAgent and formulates
        a highly readable analytics report. 
        """
        execution_success = state.get("execution_success")
        captured_output = state.get("captured_output", "")
        error_trace = state.get("error_trace", "")
        chart_image_base64 = state.get("chart_image_base64")
        query = state.get("query", "Unknown user request.")
        
        if execution_success is None:
            raise ValueError("ReportAgent requires 'execution_success' in the state context.")
            
        # 1. Handle Execution Failures gracefully
        if not execution_success:
            insights_summary = (
                "Oops! I encountered an error while executing the analysis code.\n\n"
                "**Diagnostic Trace:**\n"
                f"```python\n{error_trace}\n```\n"
                "Please consider refining your query or double-checking the dataset schema."
            )
            return {"insights_summary": insights_summary, "report_generated": True}

        # 2. Handle Execution Success - Generate Insights
        if not captured_output.strip() and not chart_image_base64:
            insights_summary = (
                "The analysis ran successfully, but no direct textual data was outputted. "
                "If a chart was generated, please check the output directory."
            )
            return {"insights_summary": insights_summary, "report_generated": True}

        # Construct a prompt for the LLM Analyst
        additional_chart_note = (
            "\nA chart image was generated and saved as output_plot.png. "
            "Use this information to help reason about the analysis and mention the visualization clearly in the response. "
            "If the chart is present, the final summary should discuss what the chart shows and why it matters."
            if chart_image_base64 else ""
        )

        prompt = f"""You are an Expert Data Analyst presenting findings to a stakeholder.
The stakeholder asked: "{query}"

I have run the analytical code on the dataset, and here is the exact raw output from the console:
=== RAW COMPUTATION OUTPUT ===
{captured_output}
==============================
{additional_chart_note}

Based on this raw output and the generated chart (if present), write a clear, concise, and professional insights summary answering the stakeholder's question.
- If a chart was generated, mention the chart in the summary and explain the key pattern or relationship it illustrates.
- DO NOT mention the python code, terminal, or "the output above".
- Act as if YOU analyzed the data yourself.
- Use markdown formatting (bullet points, bold text) to make it highly readable.
- Strictly base all numbers, statistics, and findings exclusively on the raw computation output.
- Do NOT fabricate, assume, or infer numbers that do not appear in the computation output.
- If a metric is NaN, missing, or could not be computed, state that fact explicitly without guessing.
"""
        
        try:
            # Query the centralized LLMService
            insights_summary = await self.llm_service.generate_response(
                prompt=prompt,
                temperature=0.3, # Slightly higher temperature for fluent natural language
                max_tokens=1024
            )
            
        except Exception as e:
            # Fallback if LLM summarization fails (API down, rate limits, etc.)
            insights_summary = f"Analysis succeeded, but LLM summarization failed: {str(e)}\n\n**Raw Output:**\n{captured_output}"

        return {
            "insights_summary": insights_summary,
            "report_generated": True
        }
