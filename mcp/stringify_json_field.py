#!/usr/bin/env python3
"""
Stringify JSON Field Tool

Takes a JSON object, stringifies it with proper formatting,
and replaces a specified field in a journey JSON file using sequential text search.

Works even if the journey JSON is malformed! Path must start with node ID.

Usage:
    python3 stringify_json_field.py <inner_json_path> <journey_json_path> <field_path>

Example:
    python3 stringify_json_field.py schema.json journey.json "node-id-123/action/form_schema/value"

Note: The field_path must start with the node ID, followed by the path within that node.
"""

import json
import os
import re
import sys
from typing import Any

# Import security validator
try:
    from security_validator import validate_and_sanitize
except ImportError:
    # Fallback if security_validator not available
    def validate_and_sanitize(file_path: str) -> str:
        return os.path.basename(file_path)


def load_json_file(file_path: str) -> Any:
    """Load and parse a JSON file."""
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    with open(file_path, "r") as f:
        return json.load(f)


def stringify_json_for_journey(data: Any, indent: int = 2) -> str:
    """
    Stringify JSON for journey fields with proper formatting.

    Creates a JSON string with proper indentation. The actual newlines will be
    automatically converted to \\n notation when embedded in JSON.
    """
    json_str = json.dumps(data, indent=indent, ensure_ascii=False)
    return json_str


def escape_for_json_string(value: str) -> str:
    """
    Escape a string value to be embedded as a JSON string value.
    
    This handles:
    - Backslashes -> \\
    - Quotes -> \"
    - Newlines -> \n (literal backslash-n)
    - Tabs -> \t
    - etc.
    """
    # Use json.dumps to properly escape the string
    # This will add quotes around it, so we strip them
    escaped = json.dumps(value, ensure_ascii=False)
    # Remove the surrounding quotes that json.dumps added
    if escaped.startswith('"') and escaped.endswith('"'):
        escaped = escaped[1:-1]
    return escaped


def find_node_in_nodes_section(text: str, node_id: str) -> int | None:
    """
    Find the node ID within the nodes section.

    Searches for: "<node_id>": {
    This ensures we're finding it as a key in nodes, not in a link.

    Returns the position after the opening brace, or None if not found.
    """
    # Look for the node ID as a key with opening brace
    node_pattern = rf'"{re.escape(node_id)}"\s*:\s*{{'
    match = re.search(node_pattern, text)

    if not match:
        return None

    # Return the position right after the opening brace
    return match.end()


def find_field_after_position(text: str, start_pos: int, field_name: str) -> int | None:
    """
    Find a field starting from a given position.

    Searches for: "<field_name>":

    Returns the position right after the colon, or None if not found.
    """
    # Search only in the text after start_pos
    search_text = text[start_pos:]

    field_pattern = rf'"{re.escape(field_name)}"\s*:\s*'
    match = re.search(field_pattern, search_text)

    if not match:
        return None

    # Return absolute position (not relative to search_text)
    return start_pos + match.end()


def find_string_value_bounds(text: str, start_pos: int) -> tuple[int, int] | None:
    """
    Find the start and end positions of a string value.

    Assumes the value at start_pos is a string (starts with ").
    Handles escaped quotes correctly.

    Returns (opening_quote_pos, closing_quote_pos) or None if not found.
    """
    # Skip whitespace to find the opening quote
    i = start_pos
    while i < len(text) and text[i].isspace():
        i += 1

    if i >= len(text) or text[i] != '"':
        return None

    opening_quote = i
    i += 1  # Move past opening quote

    # Find the closing quote, handling escapes
    while i < len(text):
        if text[i] == "\\":
            # Skip escaped character
            i += 2
        elif text[i] == '"':
            # Found closing quote
            return (opening_quote, i)
        else:
            i += 1

    return None


def replace_field_value_sequential(
    text: str, field_path: str, new_value: str
) -> tuple[str, bool]:
    """
    Replace a field value using sequential search from node ID.

    Args:
        text: The journey JSON text (can be malformed)
        field_path: Path starting with node ID, e.g. "node-123/action/form_schema/value"
        new_value: The new value to insert (already properly escaped)

    Returns:
        (modified_text, success)
    """
    # Split the path
    parts = field_path.replace(".", "/").split("/")

    if len(parts) < 2:
        print("  ⚠️  Path must have at least node_id and one field")
        return text, False

    node_id = parts[0]
    field_parts = parts[1:]

    print(f"  Node ID: {node_id}")
    print(f"  Field path within node: {' -> '.join(field_parts)}")

    # Step 1: Find the node in the nodes section
    pos = find_node_in_nodes_section(text, node_id)
    if pos is None:
        print(f'  ⚠️  Could not find node "{node_id}" in nodes section')
        print(f'      (Looking for pattern: "{node_id}": {{)')
        return text, False

    print(f"  ✓ Found node at position {pos}")

    # Step 2: Sequentially search for each field in the path
    for field_name in field_parts:
        # Skip array indices - they don't appear as field names
        if field_name.isdigit():
            print(f"  → Skipping array index [{field_name}]")
            continue

        pos = find_field_after_position(text, pos, field_name)
        if pos is None:
            print(f'  ⚠️  Could not find field "{field_name}" after previous position')
            return text, False
        print(f'  ✓ Found "{field_name}" at position {pos}')

    # Step 3: Find the string value boundaries
    bounds = find_string_value_bounds(text, pos)
    if bounds is None:
        print(f"  ⚠️  Could not find string value at position {pos}")
        print(f"      Make sure the field contains a string value")
        return text, False

    opening_quote, closing_quote = bounds
    print(f"  ✓ Found string value from position {opening_quote} to {closing_quote}")

    # Step 4: Replace everything between the quotes
    # Keep the opening quote, replace content, keep the closing quote
    new_text = (
        text[: opening_quote + 1]  # Everything up to and including opening quote
        + new_value  # New escaped value
        + text[closing_quote:]  # Closing quote and everything after
    )

    return new_text, True


def main():
    if len(sys.argv) != 4:
        print(
            "Usage: python3 stringify_json_field.py <inner_json_path> <journey_json_path> <field_path>"
        )
        print()
        print("Example:")
        print(
            '  python3 stringify_json_field.py schema.json journey.json "node-id-123/action/form_schema/value"'
        )
        print()
        print(
            "Field path must start with the NODE ID, followed by the path within that node."
        )
        print("This tool works even if the journey JSON is malformed!")
        print()
        print("Example paths:")
        print('  "f1a2b3c4-d5e6-7890-1234-567890abcdef/action/form_schema/value"')
        print('  "node-abc-123/links/0/data_json_schema/value"')
        sys.exit(1)

    inner_json_path = sys.argv[1]
    journey_json_path = sys.argv[2]
    field_path = sys.argv[3]

    # Security validation
    inner_filename = validate_and_sanitize(inner_json_path)
    journey_filename = validate_and_sanitize(journey_json_path)

    try:
        # Load the inner JSON to stringify
        print(f"Loading inner JSON from: {inner_filename}")
        inner_json = load_json_file(inner_json_path)

        # Stringify the inner JSON with proper formatting
        print("Stringifying inner JSON...")
        stringified = stringify_json_for_journey(inner_json)

        print(f"Stringified JSON preview: {stringified[:100]}...")

        # Escape for embedding in JSON
        escaped = escape_for_json_string(stringified)

        print(f"Escaped for JSON: {escaped[:100]}...")

        # Read the journey file as text (works even if JSON is broken!)
        print(f"Reading journey file as text: {journey_filename}")
        with open(journey_json_path, "r") as f:
            journey_text = f.read()

        # Replace the field value using sequential search
        print(f"Replacing field at path: {field_path}")
        new_text, success = replace_field_value_sequential(
            journey_text, field_path, escaped
        )

        if not success:
            print(f"❌ Could not replace field '{field_path}' in the journey JSON")
            sys.exit(1)

        # Write back to the journey JSON file
        print(f"Writing updated journey to: {journey_filename}")
        with open(journey_json_path, "w") as f:
            f.write(new_text)

        print("✅ Successfully updated journey JSON with stringified field")

        # Try to validate the result is valid JSON
        try:
            json.loads(new_text)
            print("✅ Result is valid JSON")
        except json.JSONDecodeError as e:
            print(f"⚠️  Warning: Result may not be valid JSON: {e}")
            print(
                "   The field was replaced, but there may be other issues in the file."
            )

    except FileNotFoundError as e:
        # FileNotFoundError from security_validator is already sanitized
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(
            f"❌ Inner JSON parsing error at line {e.lineno}, column {e.colno}",
            file=sys.stderr,
        )
        print(f"   {e.msg}")
        print("   The inner JSON must be valid")
        sys.exit(1)
    except Exception as e:
        # Don't print full exception details to avoid leaking paths
        print(f"❌ Unexpected error: {type(e).__name__}", file=sys.stderr)
        print(f"   {str(e)[:200]}")  # Limit error message length
        sys.exit(1)


if __name__ == "__main__":
    main()
