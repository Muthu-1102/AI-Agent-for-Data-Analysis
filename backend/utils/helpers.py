import os
import re
import json
import csv
from datetime import datetime
from typing import Any, Dict, List, Optional


# ─────────────────────────────────────────────
# FILE HANDLING
# ─────────────────────────────────────────────

def resolve_dataset_path(file_id: str, data_dir: str = "data") -> str:
    """
    Resolves a dataset file_id to its absolute path on disk.
    Searches both the given data_dir and one level up (../data/) as a fallback.
    
    Raises:
        FileNotFoundError: If the dataset cannot be located.
    """
    candidates = [
        os.path.join(data_dir, file_id),
        os.path.join("..", data_dir, file_id),
        file_id,  # treat as a raw absolute path last
    ]
    for path in candidates:
        if os.path.exists(path):
            return os.path.abspath(path)
    raise FileNotFoundError(
        f"Dataset '{file_id}' could not be located. Searched: {candidates}"
    )


def ensure_dir(directory: str) -> str:
    """
    Ensures the given directory exists, creating it (and any parents) if necessary.
    Returns the directory path for convenient chaining.
    """
    os.makedirs(directory, exist_ok=True)
    return directory


def get_file_extension(filename: str) -> str:
    """Returns the lowercase file extension including the dot (e.g. '.csv')."""
    return os.path.splitext(filename)[-1].lower()


def is_valid_csv(filename: str) -> bool:
    """Quick check that a filename has a .csv extension."""
    return get_file_extension(filename) == ".csv"


def read_text_file(path: str, encoding: str = "utf-8") -> str:
    """Reads and returns the full text content of a file."""
    with open(path, "r", encoding=encoding) as f:
        return f.read()


def write_text_file(path: str, content: str, encoding: str = "utf-8") -> None:
    """Writes a string to a file, overwriting it if it already exists."""
    ensure_dir(os.path.dirname(path) or ".")
    with open(path, "w", encoding=encoding) as f:
        f.write(content)


# ─────────────────────────────────────────────
# FORMATTING
# ─────────────────────────────────────────────

def format_timestamp(dt: Optional[datetime] = None, fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    """Returns a formatted timestamp string. Defaults to the current UTC time."""
    return (dt or datetime.utcnow()).strftime(fmt)


def truncate_string(text: str, max_length: int = 200, suffix: str = "...") -> str:
    """Truncates a string to max_length characters, appending a suffix if cut."""
    if len(text) <= max_length:
        return text
    return text[: max_length - len(suffix)] + suffix


def format_dict_as_markdown_table(data: List[Dict[str, Any]]) -> str:
    """
    Converts a list of flat dictionaries into a neatly formatted Markdown table.
    Useful for embedding data samples inside LLM prompts.
    
    Example:
        [{"Name": "Alice", "Age": 30}]  →  | Name  | Age |
                                             |-------|-----|
                                             | Alice |  30 |
    """
    if not data:
        return "_No data available._"

    headers = list(data[0].keys())
    rows = [[str(row.get(h, "")) for h in headers] for row in data]

    col_widths = [max(len(h), max((len(r[i]) for r in rows), default=0)) for i, h in enumerate(headers)]

    def pad(val: str, width: int) -> str:
        return val.ljust(width)

    header_row = "| " + " | ".join(pad(h, col_widths[i]) for i, h in enumerate(headers)) + " |"
    separator  = "| " + " | ".join("-" * w for w in col_widths) + " |"
    body_rows  = ["| " + " | ".join(pad(row[i], col_widths[i]) for i in range(len(headers))) + " |"
                  for row in rows]

    return "\n".join([header_row, separator] + body_rows)


def bytes_to_human_readable(num_bytes: int) -> str:
    """Converts a raw byte count to a human-readable string (e.g., '3.2 MB')."""
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if num_bytes < 1024.0:
            return f"{num_bytes:.1f} {unit}"
        num_bytes /= 1024.0
    return f"{num_bytes:.1f} PB"


# ─────────────────────────────────────────────
# PARSING
# ─────────────────────────────────────────────

def extract_code_block(text: str) -> str:
    """
    Extracts the first fenced Python code block from a raw LLM response string.
    Falls back to the stripped raw text if no block is found.
    
    Handles both ```python ... ``` and ``` ... ``` variants.
    """
    pattern = r"```(?:python)?\s*(.*?)\s*```"
    match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    # Strip stray fence markers and return as-is
    clean = re.sub(r"^```\w*\s*", "", text.strip())
    clean = re.sub(r"\s*```$", "", clean)
    return clean.strip()


def parse_json_safely(text: str) -> Optional[Dict[str, Any]]:
    """
    Attempts to parse a JSON string, returning None instead of raising on failure.
    Also handles LLM responses that wrap JSON in a markdown code block.
    """
    # Strip a possible ```json ... ``` wrapper
    stripped = re.sub(r"^```(?:json)?\s*", "", text.strip(), flags=re.IGNORECASE)
    stripped = re.sub(r"\s*```$", "", stripped)
    try:
        return json.loads(stripped)
    except (json.JSONDecodeError, ValueError):
        return None


def parse_csv_headers(file_path: str, encoding: str = "utf-8") -> List[str]:
    """
    Reads only the header row of a CSV file without loading the entire dataset.
    Useful for lightweight schema inspection.
    """
    with open(file_path, "r", encoding=encoding, newline="") as f:
        reader = csv.reader(f)
        headers = next(reader, [])
    return headers


def sanitize_column_name(name: str) -> str:
    """
    Converts an arbitrary column name into a safe Python identifier.
    e.g. 'Total Sales ($)' → 'total_sales_'
    """
    name = name.strip().lower()
    name = re.sub(r"[^\w\s]", "_", name)   # replace non-word chars with _
    name = re.sub(r"\s+", "_", name)         # replace whitespace with _
    name = re.sub(r"_+", "_", name)          # collapse multiple underscores
    return name.strip("_")
