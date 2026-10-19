"""
model_client.py

Wraps a single call to the Anthropic API: takes serialized messy-sheet text,
asks the model to clean it into our fixed schema (via tool-use, so we get
structured JSON back instead of free text), validates the response, and
returns it.

Swapping which model powers the tool is a one-line change: pass a different
`model` string into `clean_with_model()`. That's what makes the 3-model
comparison in the eval step trivial.
"""

import json
from pathlib import Path
from dotenv import load_dotenv
import anthropic
load_dotenv()
from src.schema import CLEAN_TABLE_SCHEMA, validate_clean_table, SchemaValidationError

client = anthropic.Anthropic()

PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "clean_prompt.txt"


class ModelClientError(Exception):
    """Raised when the model call fails or returns unusable output."""
    pass


def _load_prompt_template() -> str:
    return PROMPT_PATH.read_text()


def clean_with_model(serialized_text: str, model: str, max_tokens: int = 1000) -> tuple:
    """Send serialized sheet text to `model`, return validated clean-table dict and usage data.

    Returns a dict shaped like:
        {"columns": [...], "rows": [...]}
    (Same shape schema.py validates -- see schema.py for details.)

    Raises ModelClientError if the API call fails or the response can't be
    validated even after we've tried to extract the tool-use block.
    """
    prompt_template = _load_prompt_template()
    user_prompt = prompt_template.format(sheet_text=serialized_text)

    try:
        response = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            tools=[CLEAN_TABLE_SCHEMA],
            tool_choice={"type": "tool", "name": "clean_table"},
            messages=[{"role": "user", "content": user_prompt}],
        )
    except anthropic.APIError as e:
        raise ModelClientError(f"API call failed for model {model}: {e}") from e

    # 

    # With tool_choice forcing "clean_table", the model's structured output
    # comes back as a tool_use block's `input` field, not as plain text.
    tool_use_block = next(
        (block for block in response.content if block.type == "tool_use"), None
    )
    if tool_use_block is None:
        raise ModelClientError(
            f"Model {model} did not return a tool_use block. Raw response: {response.content}"
        )

    data = tool_use_block.input

    try:
        validate_clean_table(data)
    except SchemaValidationError as e:
        raise ModelClientError(f"Model {model} returned invalid schema: {e}") from e

    # Also call and return cost usage to cli to display to user
    usage_and_cost = get_usage_and_cost(response, model)
    return data, usage_and_cost


def get_usage_and_cost(response, model: str) -> dict:
    """Return a dict with usage and cost info for the given model response."""
    usage = response.usage
    input_tokens = usage.input_tokens
    output_tokens = usage.output_tokens

    # return token cost
    return {
        "model": model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": input_tokens + output_tokens,
    }
