# Spreadsheet Cleaner

A Python command-line project that converts a messy CSV or Excel spreadsheet into a structured CSV. The project sends the spreadsheet to an Anthropic model, validates the model's response against a fixed schema, and writes the cleaned data with confidence scores and notes.

## How the project works

1. `clean.py` receives the input file, output path, model name, and optional output-token limit.
2. `src.serializer` reads the CSV or Excel workbook and converts it into text.
3. `src.model_client` inserts that text into the prompt and calls the selected Anthropic model.
4. `src.schema` validates that the model returned the expected columns and rows.
5. `src.writer` writes the validated result to the requested CSV file.

## Prerequisites

Before running the project, make sure you have:

- Python 3.9 or later
- An Anthropic API key with access to the model you want to test
- Internet access for the Anthropic API
- A terminal with the project virtual environment activated

The project dependencies are listed in [requirements.txt](requirements.txt):

- `anthropic`
- `openpyxl`
- `python-dotenv`
- The supporting `httpx`, `pydantic`, and other packages required by Anthropic

## Setup

### 1. Open the project directory

```bash
cd "/home/loudlad/Desktop/Lab 2 Project"
```

### 2. Create or reuse the virtual environment

If the virtual environment does not already exist:

```bash
python3 -m venv venv
```

Activate it:

```bash
source venv/bin/activate
```

### 3. Install the dependencies

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

If the project is already using the existing virtual environment, confirm that the packages are installed:

```bash
python -m pip check
```

### 4. Configure the Anthropic API key

Create or update the `.env` file in the project root:

```dotenv
ANTHROPIC_API_KEY=your_api_key_here
```

The application loads this value through `python-dotenv`. Do not commit the `.env` file or include the API key in command-line arguments.

Verify that the key is available:

```bash
python -c "from dotenv import load_dotenv; load_dotenv(); import os; print('ANTHROPIC_API_KEY is set' if os.getenv('ANTHROPIC_API_KEY') else 'ANTHROPIC_API_KEY is missing')"
```

## Run the project

Place your input file in a location accessible from the project directory. The input may be a `.csv`, `.xlsx`, or `.xlsm` file.

Run the cleaning command:

```bash
python clean.py \
  --input path/to/input.csv \
  --output results/cleaned_output.csv \
  --model claude-sonnet-4-6
```

Replace the paths and model name with your values. The output directory is created automatically if it does not exist.

The command performs the following steps:

1. Serializes the spreadsheet.
2. Sends the serialized data to the selected model.
3. Validates the returned structured data.
4. Writes the cleaned CSV.

### Command options

```text
--input PATH       Input CSV, XLSX, or XLSM file (required)
--output PATH      Output CSV file (required)
--model NAME       Anthropic model name (required)
--max-tokens N     Maximum output tokens (default: 1000)
```

For a larger result set, increase the output limit:

```bash
python clean.py \
  --input path/to/input.xlsx \
  --output results/cleaned_output.csv \
  --model claude-sonnet-4-6 \
  --max-tokens 4096
```

## Output file

The output CSV contains the cleaned columns followed by two additional columns:

- `confidence`: a number from `0` to `1` when the model had to infer or interpret a value; otherwise blank
- `notes`: a short explanation of the uncertainty when `confidence` is populated; otherwise blank

The same input file can be run against a different model by changing only the `--model` value.

## Model comparison table

| Model used | Input tokens | Output tokens | Total tokens | Total cost (USD) |
| ---------- | ------------ | ------------- | ------------ | ---------------- |
| claude-sonnet-4-5|3065|2178|5243|$0.0419|
| claude-haiku-4-5-2   | 3065 |2346|5411|$0.0148|
| claude-opus-4-5 |3065| 2038|5103|$0.0663|

Calculated the total as:

```text
Total tokens = Input tokens + Output tokens
```

## Notes

- The project uses the Anthropic API directly; no separate API server is required.
- Use the same input file for every model comparison.
- Keep the API key in `.env` and never place it in source code or command-line arguments.
- The current `get_usage_and_cost()` helper is not used by the CLI.
