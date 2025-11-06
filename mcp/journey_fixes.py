#!/usr/bin/env python3
"""
Journey Fixes - Auto-fix common issues in journey JSON files.

This module provides auto-fix functions for journey JSON files:

ALWAYS-RUN FIXES (called by main()):
- Over-escaped quotes and backslashes (multiple levels)
- Invalid journey types
- Missing timestamps and metadata
- Invalid UUIDs
- Loop/block body mismatches
- Internal backticks in expressions
- Missing backticks in conditions and loops
- Excessive backticking in information nodes
- Incorrect link types (branch vs escape)
- Missing metadata field in auth_pass and reject action nodes
- Deprecated get_information action type (converts to form structure)
- Strict equality operators (=== to ==, !== to !=)

VALIDATOR-SPECIFIC FIXES (called by validators):
- Variable initialization (used by validate_journey_variables.py)
  - auto_fix_uninitialized_variables() - Adds variables to set_variables
  - auto_fix_variable_field_initialization() - Adds missing fields to initialized variables
  - find_or_create_initial_set_variables_node() - Helper to find/create set_variables node
  - add_variable_to_set_variables_node() - Helper to add a variable
  - update_variable_initialization_with_fields() - Helper to add fields to existing variable

These validator-specific fixes are NOT part of main() to allow validators
to control when and how they're applied, with proper warning messages and
re-validation.
"""

import json
import os
import re
import sys
import time
import uuid
from typing import Tuple

# Import security validator
try:
    from security_validator import validate_and_sanitize
except ImportError:
    # Fallback if security_validator not available
    def validate_and_sanitize(file_path: str) -> str:
        return os.path.basename(file_path)


# Load node definitions
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
NODE_DEFS_PATH = os.path.join(SCRIPT_DIR, "node_definitions.json")

try:
    with open(NODE_DEFS_PATH, "r") as f:
        NODE_DEFINITIONS = json.load(f)
        NODE_DEFS = NODE_DEFINITIONS["nodes"]
        CONSTANTS = NODE_DEFINITIONS["constants"]
except Exception as e:
    print(f"⚠️  Warning: Could not load node_definitions.json: {e}")
    print("   Some fixes may not work correctly.")
    NODE_DEFS = {}
    CONSTANTS = {}

# Global to track if any auto-fixes were applied
AUTO_FIXES_APPLIED = []


def log_auto_fix(fix_description: str):
    """Log an auto-fix that was applied."""
    AUTO_FIXES_APPLIED.append(fix_description)
    print(f"  ⚙️  AUTO-FIXED: {fix_description}")


def fix_raw_json_escaping(file_path: str) -> tuple:
    """Auto-fix over-escaped strings in raw JSON file BEFORE parsing.

    Fixes patterns like (in the raw JSON file, as you see it in editor):
        "value": "[\\n  {\\"key\\":\\"val\\"}]"  ← WRONG (double backslash before escape chars)
    To:
        "value": "[\n  {\"key\":\"val\"}]"       ← CORRECT (single backslash before escape chars)

    This operates on the RAW FILE TEXT before json.load() is called.

    Runs multiple passes to handle multiple levels of over-escaping.

    Returns: (modified_text, fixes_applied_count)
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            raw_text = f.read()
    except Exception as e:
        print(f"Warning: Could not read file for escaping fixes: {e}")
        return "", 0

    original_text = raw_text
    total_fixes_count = 0

    # Fix all common over-escaped sequences
    escape_fixes = [
        ('\\\\"', '\\"'),  # \\" → \"  (quotes)
        ("\\\\n", "\\n"),  # \\n → \n  (newlines)
        ("\\\\t", "\\t"),  # \\t → \t  (tabs)
        ("\\\\r", "\\r"),  # \\r → \r  (carriage returns)
        ("\\\\/", "\\/"),  # \\/ → \/  (forward slash)
    ]

    # Keep applying fixes until no more changes are made
    # (handles multiple levels of over-escaping)
    max_passes = 10  # Safety limit to prevent infinite loops
    pass_num = 0

    while pass_num < max_passes:
        pass_num += 1
        fixes_this_pass = 0

        for pattern, replacement in escape_fixes:
            count = raw_text.count(pattern)
            if count > 0:
                raw_text = raw_text.replace(pattern, replacement)
                fixes_this_pass += count

        total_fixes_count += fixes_this_pass

        # If no fixes were made this pass, we're done
        if fixes_this_pass == 0:
            break

    # If we made changes, save the file
    if total_fixes_count > 0:
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(raw_text)
            return raw_text, total_fixes_count
        except Exception as e:
            print(f"Warning: Could not save escaping fixes: {e}")
            return raw_text, total_fixes_count

    return raw_text, 0


def fix_journey_metadata(journey_json: dict) -> None:
    """Auto-fix invalid journey types."""
    valid_journey_types = CONSTANTS.get("valid_journey_types", ["anonymous"])

    if "exports" in journey_json and isinstance(journey_json["exports"], list):
        if len(journey_json["exports"]) > 0 and "data" in journey_json["exports"][0]:
            data = journey_json["exports"][0]["data"]
            journey_type = data.get("type")

            if journey_type not in valid_journey_types:
                action = f"Changed invalid journey type '{journey_type}'" if journey_type else "Added missing journey type"
                data["type"] = "anonymous"
                log_auto_fix(f"{action} to 'anonymous'")


def fix_journey_required_fields(journey_json: dict) -> None:
    """Auto-fix missing timestamps and metadata."""
    if "exports" in journey_json and isinstance(journey_json["exports"], list):
        if len(journey_json["exports"]) > 0 and "data" in journey_json["exports"][0]:
            data = journey_json["exports"][0]["data"]
            current_time_ms = int(
                time.time() * 1000
            )  # Milliseconds for top-level timestamps
            current_time = int(time.time())  # Seconds for version timestamps
            one_hour_ago_ms = current_time_ms - (3600 * 1000)
            one_hour_ago = current_time - 3600

            # Fix top-level data timestamps (in milliseconds with _date suffix)
            for ts_field in ["created_date", "last_modified_date"]:
                if ts_field not in data:
                    data[ts_field] = current_time_ms
                    log_auto_fix(f"Added missing '{ts_field}' timestamp to data: {current_time_ms}")
                elif isinstance(data.get(ts_field), (int, float)):
                    timestamp = data[ts_field]
                    if timestamp < one_hour_ago_ms:
                        from datetime import datetime
                        old_timestamp_dt = datetime.fromtimestamp(timestamp / 1000)
                        data[ts_field] = current_time_ms
                        log_auto_fix(
                            f"Updated '{ts_field}' from {old_timestamp_dt.strftime('%Y-%m-%d %H:%M:%S')} "
                            f"to current time: {current_time_ms}"
                        )
                    elif timestamp > current_time_ms + 60000:
                        data[ts_field] = current_time_ms
                        log_auto_fix(f"Updated '{ts_field}' from future timestamp {timestamp} to current time: {current_time_ms}")

            # Check for required top-level data fields
            if "versions" not in data:
                data["versions"] = []
                log_auto_fix("Added missing 'versions' array to journey data")

            # Check versions array
            if "versions" in data and isinstance(data["versions"], list):
                if len(data["versions"]) > 0:
                    version = data["versions"][0]

                    # Set default values for missing fields
                    defaults = {
                        "state": ("version", "Added missing 'state' field with default value 'version'"),
                        "desc": ("Generated journey", "Added missing 'desc' field with default description"),
                        "created_at": (current_time, f"Added missing 'created_at' timestamp to version: {current_time}"),
                        "last_modified": (current_time, f"Added missing 'last_modified' timestamp to version: {current_time}"),
                    }
                    for field, (default_value, log_message) in defaults.items():
                        if field not in version:
                            version[field] = default_value
                            log_auto_fix(log_message)

                    # Validate and fix version timestamps (in seconds)
                    for ts_field in ["created_at", "last_modified"]:
                        if ts_field in version:
                            timestamp = version[ts_field]

                            # Check if it's a valid number
                            if not isinstance(timestamp, (int, float)):
                                continue

                            # Auto-fix: timestamp too old (more than 1 hour ago)
                            if timestamp < one_hour_ago:
                                from datetime import datetime

                                old_timestamp_dt = datetime.fromtimestamp(timestamp)
                                version[ts_field] = current_time
                                log_auto_fix(
                                    f"Updated version '{ts_field}' from {old_timestamp_dt.strftime('%Y-%m-%d %H:%M:%S')} "
                                    f"to current time: {current_time}"
                                )

                            # Auto-fix: timestamp in the future
                            elif timestamp > current_time + 60:
                                version[ts_field] = current_time
                                log_auto_fix(
                                    f"Updated version '{ts_field}' from future timestamp {timestamp} "
                                    f"to current time: {current_time}"
                                )

                    # Validate state field
                    if "state" in version:
                        state = version["state"]
                        valid_states = CONSTANTS.get(
                            "valid_version_states",
                            ["disabled", "version", "production", "legacy", "obsolete"],
                        )
                        if state not in valid_states:
                            version["state"] = "version"
                            log_auto_fix(
                                f"Changed invalid state '{state}' to 'version'"
                            )


def fix_invalid_uuids(workflow: dict) -> None:
    """Auto-fix invalid UUIDs by generating valid ones and replacing consistently."""
    uuid_pattern = r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"

    # Step 1: Collect all invalid IDs and create mapping
    uuid_mapping = {}  # invalid_id -> valid_uuid

    # Check node dictionary keys
    for node_id in workflow["nodes"].keys():
        if not re.match(uuid_pattern, node_id):
            uuid_mapping[node_id] = str(uuid.uuid4())

    # Check workflow head
    if "head" in workflow and not re.match(uuid_pattern, workflow["head"]):
        head_id = workflow["head"]
        if head_id not in uuid_mapping:
            uuid_mapping[head_id] = str(uuid.uuid4())

    # If no invalid UUIDs found, nothing to do
    if not uuid_mapping:
        return

    # Step 2: Apply replacements
    new_nodes = {}
    for old_id, node in workflow["nodes"].items():
        new_id = uuid_mapping.get(old_id, old_id)

        # Replace node["id"]
        node["id"] = new_id

        # Replace link targets
        if "links" in node:
            for link in node["links"]:
                if "target" in link and link["target"]:
                    link["target"] = uuid_mapping.get(link["target"], link["target"])

        # Replace loop_body and block id references
        for body_key in [("loop", "loop_body"), ("block", "block")]:
            node_type, field_name = body_key
            if node.get("type") == node_type and field_name in node:
                if isinstance(node[field_name], dict) and "id" in node[field_name]:
                    old_id = node[field_name]["id"]
                    node[field_name]["id"] = uuid_mapping.get(old_id, old_id)

        new_nodes[new_id] = node

    # Replace the nodes dictionary
    workflow["nodes"] = new_nodes

    # Replace workflow head
    if "head" in workflow:
        workflow["head"] = uuid_mapping.get(workflow["head"], workflow["head"])

    # Log all replacements
    for old_id, new_id in uuid_mapping.items():
        log_auto_fix(f"Replaced invalid UUID '{old_id}' with valid UUID '{new_id}'")


def fix_workflow_uuids(workflow: dict) -> None:
    """Fix UUIDs in workflow."""
    uuid_pattern = r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"

    # First, fix any invalid UUIDs throughout the journey
    fix_invalid_uuids(workflow)

    # Now validate and fix node IDs
    for node_id, node in workflow["nodes"].items():
        if node.get("id") != node_id:
            action = "Fixed mismatched" if "id" in node else "Added missing"
            node["id"] = node_id
            log_auto_fix(f"{action} id for node {node_id}")

    # Fix workflow ID
    if "id" not in workflow or not re.match(uuid_pattern, workflow.get("id", "")):
        new_uuid = str(uuid.uuid4())
        workflow["id"] = new_uuid
        action = "Added missing" if "id" not in workflow else "Generated new"
        log_auto_fix(f"{action} workflow ID: {new_uuid}")


def fix_loop_and_block_body(workflow: dict) -> None:
    """Auto-fix loop_body and block mismatches by copying from nodes dictionary."""
    for node_id, node in workflow["nodes"].items():
        if node["type"] == "block" or node["type"] == "loop":
            body_key = "block" if node["type"] == "block" else "loop_body"
            body = node.get(body_key)

            if body:
                if "id" in body:
                    body_id = body["id"]
                    body_entry_node = workflow["nodes"].get(body_id)

                    if body_entry_node:
                        # The embedded definition must match the node in nodes dict exactly
                        if body_entry_node != body:
                            node[body_key] = workflow["nodes"][body_id]
                            log_auto_fix(
                                f"Node {node_id}: Synchronized '{body_key}' field with node {body_id} from nodes dictionary"
                            )


def fix_internal_backticks_in_expression(value: str) -> tuple:
    """Auto-fix internal backticks in expressions that are wrapped in outer backticks.

    Example: `menuData.action != `exit`` → menuData.action != "exit"

    Returns: (fixed_value, was_fixed)
    """
    if not value or not isinstance(value, str):
        return value, False

    # Only fix if wrapped in backticks
    if not (value.startswith("`") and value.endswith("`")):
        return value, False

    # Check if there are internal backticks
    inner_content = value[1:-1]
    if "`" not in inner_content:
        return value, False

    # Replace internal backticks with plain double quotes
    fixed_inner = inner_content.replace("`", '"')

    return f"{fixed_inner}", True


def fix_loop_conditions(workflow: dict) -> None:
    """Auto-fix loop condition expressions - remove outer backticks and fix internal backticks."""
    for node_id, node in workflow["nodes"].items():
        if node.get("type") == "loop" and "condition" in node:
            condition = node["condition"]

            # Check if condition is an expression object
            if isinstance(condition, dict) and condition.get("type") == "expression":
                value = condition.get("value", "")

                if isinstance(value, str) and value:
                    # Auto-fix internal backticks (this also removes outer backticks)
                    fixed_value, was_fixed = fix_internal_backticks_in_expression(value)
                    if was_fixed:
                        condition["value"] = fixed_value
                        log_auto_fix(
                            f"Node {node_id}: Fixed backticks in loop condition: {value} → {fixed_value}"
                        )


def fix_condition_data_types(workflow: dict) -> None:
    """Auto-fix condition node expressions - add missing backticks and fix internal backticks."""
    for node_id, node in workflow["nodes"].items():
        if node.get("type") == "condition" and "condition" in node:
            condition = node["condition"]

            # Check field and value expressions
            for field_name in ["field", "value"]:
                if field_name in condition:
                    field_obj = condition[field_name]
                    if isinstance(field_obj, dict) and field_obj.get("type") == "expression":
                        value = field_obj.get("value", "")
                        if isinstance(value, str) and value:
                            fixed_value, was_fixed = fix_internal_backticks_in_expression(value)
                            if was_fixed:
                                field_obj["value"] = fixed_value
                                log_auto_fix(
                                    f"Node {node_id}: Replaced internal backticks with escaped quotes in condition '{field_name}': {value} → {fixed_value}"
                                )


def fix_information_node_backtick_concatenation(value: str) -> tuple:
    """Auto-fix excessive backticking in information node expressions.

    Converts: `` `Username: ` + userProfile.username + ` Emails: ` + userProfile.emails ``
    To: `"Username: " userProfile.username " Emails: " userProfile.emails`

    Returns: (fixed_value, was_fixed)
    """
    if not value or not isinstance(value, str):
        return value, False

    # Check for double backticks at start/end
    has_double_backticks = False
    clean_value = value.strip()

    if clean_value.startswith("`` ") and clean_value.endswith(" ``"):
        has_double_backticks = True
        clean_value = clean_value[3:-3].strip()
    elif clean_value.startswith("``") and clean_value.endswith("``"):
        has_double_backticks = True
        clean_value = clean_value[2:-2].strip()

    # Check if there's backtick concatenation pattern
    backtick_concat_pattern = r"`[^`]*`\s*\+\s*[a-zA-Z_][a-zA-Z0-9_.]*"
    if not re.search(backtick_concat_pattern, clean_value) and not has_double_backticks:
        return value, False

    # Parse and reconstruct with proper quoting
    current_pos = 0
    result_parts = []

    while current_pos < len(clean_value):
        # Skip whitespace
        while current_pos < len(clean_value) and clean_value[current_pos].isspace():
            current_pos += 1

        if current_pos >= len(clean_value):
            break

        # Check if we're at a backticked string
        if clean_value[current_pos] == "`":
            end_pos = current_pos + 1
            while end_pos < len(clean_value) and clean_value[end_pos] != "`":
                end_pos += 1

            if end_pos < len(clean_value):
                text_content = clean_value[current_pos + 1 : end_pos]
                result_parts.append(("text", text_content))
                current_pos = end_pos + 1
        else:
            # Check if we're at a + operator
            if clean_value[current_pos] == "+":
                result_parts.append(("plus", "+"))
                current_pos += 1
                continue

            # Must be a variable name
            var_match = re.match(
                r"([a-zA-Z_][a-zA-Z0-9_.]*)", clean_value[current_pos:]
            )
            if var_match:
                var_name = var_match.group(1)
                result_parts.append(("var", var_name))
                current_pos += len(var_name)
            else:
                return value, False

    # Reconstruct: wrap in backticks, convert text to quoted strings, REMOVE + operators
    if not result_parts:
        return value, False

    reconstructed = "`"
    for i, (part_type, content) in enumerate(result_parts):
        if part_type == "text":
            if reconstructed != "`":
                reconstructed += " "
            reconstructed += f'"{content}"'
        elif part_type == "var":
            if reconstructed != "`":
                reconstructed += " "
            reconstructed += content
        elif part_type == "plus":
            pass  # Skip + operators
    reconstructed += "`"

    return reconstructed, True


def fix_set_variables_json_backticks(workflow: dict) -> None:
    """Remove unnecessary backticks from JSON objects in set_variables."""
    for node_id, node in workflow["nodes"].items():
        if node.get("type") == "action" and "action" in node:
            action = node["action"]
            if action.get("type") == "set_variables" and "variables" in action:
                for var in action["variables"]:
                    if "value" in var and isinstance(var["value"], dict):
                        if var["value"].get("type") == "expression":
                            value = var["value"].get("value", "")

                            # Remove backticks from JSON objects
                            if (
                                isinstance(value, str)
                                and value.startswith("`{")
                                and value.endswith("}`")
                            ):
                                fixed_value = value[
                                    1:-1
                                ]  # Remove first and last character
                                var["value"]["value"] = fixed_value
                                log_auto_fix(
                                    f"Node {node_id}: Removed unnecessary backticks from variable '{var['name']}': {value[:50]}... → {fixed_value[:50]}..."
                                )


def fix_link_types(workflow: dict) -> None:
    """Auto-fix incorrect link types based on node definitions.

    For example, if a 'failure' link has type 'branch' but should be 'escape',
    this will fix it automatically based on the node_definitions.json.
    """
    for node_id, node in workflow["nodes"].items():
        node_type = node.get("type")

        # Get the node definition
        node_def = None
        if node_type == "action" and "action" in node:
            action_type = node["action"].get("type")
            node_def = NODE_DEFS.get(action_type)
        elif node_type in NODE_DEFS:
            node_def = NODE_DEFS.get(node_type)

        if not node_def or "required_links" not in node_def:
            continue

        required_links = node_def["required_links"]

        # Build a mapping of link name -> expected type
        link_type_map = {}
        for link_type in ["branch", "escape"]:
            if link_type in required_links:
                for link_name in required_links[link_type]:
                    link_type_map[link_name] = link_type

        if not link_type_map or "links" not in node:
            continue

        # Check and fix each link
        for link in node["links"]:
            link_name = link.get("name")
            current_type = link.get("type")

            if link_name in link_type_map:
                expected_type = link_type_map[link_name]

                if current_type != expected_type:
                    link["type"] = expected_type
                    node_display = (
                        f"{node_type}/{node['action']['type']}"
                        if node_type == "action"
                        else node_type
                    )
                    log_auto_fix(
                        f"Node {node_id} ({node_display}): Fixed link '{link_name}' type from '{current_type}' to '{expected_type}'"
                    )


def fix_auth_pass_and_reject_metadata(workflow: dict) -> None:
    """Auto-fix missing metadata field in auth_pass and reject action nodes."""
    for node_id, node in workflow["nodes"].items():
        if node.get("type") == "action" and "action" in node:
            action = node["action"]
            action_type = action.get("type")

            # Check if this is an auth_pass or reject action without metadata
            if action_type in ["auth_pass", "reject"]:
                if "metadata" not in action:
                    action["metadata"] = {"type": action_type}
                    log_auto_fix(
                        f"Node {node_id}: Added missing 'metadata' field to {action_type} action node"
                    )


def fix_strict_equality_operators(workflow: dict) -> None:
    """Auto-fix strict equality operators (=== and !==) to standard operators (== and !=)."""

    def fix_expression_value(value: str, node_id: str, field_path: str) -> tuple:
        """Fix === and !== in a single expression value. Returns (fixed_value, was_fixed)"""
        if not value or not isinstance(value, str):
            return value, False

        original = value
        fixed = value
        changes = []

        # Replace !== first to avoid confusion with ===
        if "!==" in fixed:
            count = fixed.count("!==")
            fixed = fixed.replace("!==", "!=")
            changes.append(f"!== → != ({count} occurrence{'s' if count > 1 else ''})")

        # Replace ===
        if "===" in fixed:
            count = fixed.count("===")
            fixed = fixed.replace("===", "==")
            changes.append(f"=== → == ({count} occurrence{'s' if count > 1 else ''})")

        if changes:
            log_auto_fix(
                f"Node {node_id} field '{field_path}': Fixed strict equality operators: {', '.join(changes)}"
            )
            return fixed, True

        return value, False

    def check_expression_field(obj: dict, node_id: str, field_path: str):
        """Recursively check and fix expression fields in an object."""
        if isinstance(obj, dict):
            if obj.get("type") == "expression" and "value" in obj:
                value = obj.get("value", "")
                if isinstance(value, str):
                    fixed_value, was_fixed = fix_expression_value(
                        value, node_id, field_path
                    )
                    if was_fixed:
                        obj["value"] = fixed_value

            # Recurse into nested dictionaries
            for key, val in obj.items():
                if isinstance(val, dict):
                    check_expression_field(val, node_id, f"{field_path}.{key}")
                elif isinstance(val, list):
                    for i, item in enumerate(val):
                        if isinstance(item, dict):
                            check_expression_field(
                                item, node_id, f"{field_path}.{key}[{i}]"
                            )
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                if isinstance(item, dict):
                    check_expression_field(item, node_id, f"{field_path}[{i}]")

    # Check all nodes
    for node_id, node in workflow["nodes"].items():
        # Check loop conditions
        if node.get("type") == "loop" and "condition" in node:
            check_expression_field(node["condition"], node_id, "condition")

        # Check condition nodes
        if node.get("type") == "condition" and "condition" in node:
            check_expression_field(node["condition"], node_id, "condition")

        # Check action nodes
        if node.get("type") == "action" and "action" in node:
            check_expression_field(node["action"], node_id, "action")


def fix_get_information_to_form(workflow: dict) -> None:
    """Auto-fix deprecated get_information action type to form structure."""
    for node_id, node in workflow["nodes"].items():
        if node.get("type") == "action" and "action" in node:
            action = node["action"]
            if action.get("type") == "get_information":
                # Convert to form structure
                action["type"] = "form"
                if "metadata" not in action:
                    action["metadata"] = {}
                action["metadata"]["type"] = "get_information"
                log_auto_fix(
                    f"Node {node_id}: Converted deprecated 'get_information' action to form structure with metadata"
                )


def fix_information_node_expressions(workflow: dict) -> None:
    """Auto-fix excessive backticking in information nodes and add missing title field."""
    for node_id, node in workflow["nodes"].items():
        if node.get("type") == "action" and "action" in node:
            action = node["action"]
            if action.get("type") == "information":
                # Add missing title field with empty string
                if "title" not in action:
                    action["title"] = {"type": "expression", "value": '""'}
                    log_auto_fix(
                        f"Node {node_id}: Added missing 'title' field to information node with empty string value"
                    )

                # Check text, title, and button_text fields
                for field_name in ["text", "title", "button_text"]:
                    if field_name in action and isinstance(action[field_name], dict):
                        if action[field_name].get("type") == "expression":
                            field_value = action[field_name].get("value", "")
                            fixed_value, was_fixed = fix_information_node_backtick_concatenation(field_value)
                            if was_fixed:
                                action[field_name]["value"] = fixed_value
                                if field_name == "text" and len(field_value) > 80:
                                    log_auto_fix(
                                        f"Node {node_id}: Converted excessive backticking to template literal in {field_name} field:\n"
                                        f"    FROM: {field_value[:80]}...\n"
                                        f"    TO: {fixed_value[:80]}..."
                                    )
                                else:
                                    log_auto_fix(
                                        f"Node {node_id}: Converted excessive backticking to template literal in {field_name} field: {field_value} → {fixed_value}"
                                    )


def extract_workflow_from_journey(journey_json: dict) -> dict:
    """Extract workflow from journey JSON."""
    if "exports" in journey_json:
        exports = journey_json.get("exports", [])
        if isinstance(exports, list) and len(exports) > 0:
            data = exports[0].get("data", {})
            versions = data.get("versions", [])
            if len(versions) > 0:
                return versions[0].get("workflow")
    return journey_json.get("workflow")


# ============================================================================
# Variable Initialization Auto-Fixes (used by validate_journey_variables.py)
# ============================================================================


def find_or_create_initial_set_variables_node(workflow: dict) -> tuple:
    """
    Find or create a set_variables node at the start of the journey.

    Args:
        workflow: The workflow dictionary

    Returns:
        (node_id, node_dict) tuple, or (None, None) if failed
    """
    # Check if head node is already set_variables
    head_id = workflow.get("head")
    if not head_id or head_id not in workflow["nodes"]:
        return None, None

    head_node = workflow["nodes"][head_id]

    # If head is already set_variables, return it
    if (
        head_node.get("type") == "action"
        and head_node.get("action", {}).get("type") == "set_variables"
    ):
        return head_id, head_node

    # Check if head links to a set_variables as first node
    if "links" in head_node and len(head_node["links"]) > 0:
        first_link = head_node["links"][0]
        if "target" in first_link and first_link["target"]:
            first_node_id = first_link["target"]
            first_node = workflow["nodes"].get(first_node_id)
            if (
                first_node
                and first_node.get("type") == "action"
                and first_node.get("action", {}).get("type") == "set_variables"
            ):
                return first_node_id, first_node

    # Need to create a new set_variables node
    new_id = str(uuid.uuid4())

    # Get the current head's first link target (if any)
    next_node_id = None
    if "links" in head_node and len(head_node["links"]) > 0:
        next_node_id = head_node["links"][0].get("target")

    # Create new set_variables node
    new_node = {
        "id": new_id,
        "type": "action",
        "action": {"type": "set_variables", "variables": []},
        "links": [],
    }

    # Link it to the next node (if any)
    if next_node_id:
        new_node["links"].append(
            {"name": "child", "type": "branch", "target": next_node_id}
        )

    # Add to workflow
    workflow["nodes"][new_id] = new_node

    # Update head to point to new node
    if "links" not in head_node:
        head_node["links"] = []

    if len(head_node["links"]) == 0:
        head_node["links"].append({"name": "child", "type": "branch", "target": new_id})
    else:
        head_node["links"][0]["target"] = new_id

    log_auto_fix(f"Created new set_variables node {new_id} at the start of the journey")

    return new_id, new_node


def add_variable_to_set_variables_node(
    node: dict, var_name: str, var_value: str = "null"
) -> bool:
    """
    Add a variable to a set_variables node if it doesn't already exist.

    Args:
        node: The set_variables node
        var_name: Name of the variable to add
        var_value: Value to initialize the variable with (default: "null")

    Returns:
        True if variable was added, False if it already exists or failed
    """
    if "action" not in node or "variables" not in node["action"]:
        return False

    variables = node["action"]["variables"]

    # Check if variable already exists
    for var in variables:
        if var.get("name") == var_name:
            return False  # Already exists

    # Add the variable
    variables.append(
        {"name": var_name, "value": {"type": "expression", "value": var_value}}
    )

    log_auto_fix(
        f"Added variable '{var_name}' with value '{var_value}' to set_variables node"
    )

    return True


def auto_fix_uninitialized_variables(workflow: dict, uninitialized_vars: list) -> int:
    """
    Auto-fix uninitialized variables by adding them to a set_variables node.

    This function is called by validate_journey_variables.py to fix variables
    that are referenced but not initialized.

    Args:
        workflow: The workflow dictionary
        uninitialized_vars: List of variable names to initialize

    Returns:
        Number of variables that were successfully added
    """
    if not uninitialized_vars:
        return 0

    # Find or create set_variables node
    node_id, set_vars_node = find_or_create_initial_set_variables_node(workflow)
    if not node_id or not set_vars_node:
        return 0

    # Add each uninitialized variable
    added_count = 0
    for var_name in uninitialized_vars:
        if add_variable_to_set_variables_node(set_vars_node, var_name, "null"):
            added_count += 1

    return added_count


def update_variable_initialization_with_fields(
    workflow: dict, var_name: str, required_fields: list
) -> bool:
    """
    Update a variable's initialization to include required fields.

    This is used when a variable is initialized as null or empty object,
    but fields are accessed on it elsewhere in the journey.

    Args:
        workflow: The workflow dictionary
        var_name: Name of the variable to update
        required_fields: List of field names that need to be in the initialization

    Returns:
        True if the variable was updated, False otherwise
    """
    if not required_fields:
        return False

    # Find all set_variables nodes
    for node_id, node in workflow["nodes"].items():
        if node.get("type") == "action" and "action" in node:
            action = node["action"]
            if action.get("type") == "set_variables" and "variables" in action:
                # Look for the variable in this node
                for var in action["variables"]:
                    if var.get("name") == var_name:
                        # Found the variable - update its initialization
                        if "value" in var and isinstance(var["value"], dict):
                            if var["value"].get("type") == "expression":
                                current_value = var["value"].get("value", "")

                                # Parse current value
                                try:
                                    # Handle null or empty object
                                    if current_value == "null" or current_value in ["{}", "`{}`", '"{}"']:
                                        field_pairs = [f'"{field}": ""' for field in required_fields]
                                        new_value = "{" + ", ".join(field_pairs) + "}"
                                        var["value"]["value"] = new_value
                                        from_value = "null" if current_value == "null" else "empty object"
                                        log_auto_fix(
                                            f"Updated variable '{var_name}' initialization from {from_value} to object with fields: {required_fields}"
                                        )
                                        return True

                                    # Try to parse as JSON and merge fields
                                    else:
                                        # Remove outer backticks if present
                                        json_str = current_value
                                        if json_str.startswith(
                                            "`"
                                        ) and json_str.endswith("`"):
                                            json_str = json_str[1:-1]

                                        try:
                                            current_obj = json.loads(json_str)
                                            if isinstance(current_obj, dict):
                                                # Add missing fields
                                                added_fields = []
                                                for field in required_fields:
                                                    if field not in current_obj:
                                                        current_obj[field] = ""
                                                        added_fields.append(field)

                                                if added_fields:
                                                    # Serialize back to JSON string (unescaped - json.dump will escape it)
                                                    new_value = json.dumps(current_obj)
                                                    var["value"]["value"] = new_value
                                                    log_auto_fix(
                                                        f"Added missing fields {added_fields} to variable '{var_name}' initialization"
                                                    )
                                                    return True
                                        except (json.JSONDecodeError, ValueError):
                                            # Can't parse - skip
                                            pass

                                except Exception:
                                    # If anything goes wrong, skip this variable
                                    pass

    return False


def auto_fix_variable_field_initialization(workflow: dict, var_fields_map: dict) -> int:
    """
    Auto-fix variable initializations to include required fields.

    This function is called by validate_journey_variables.py when variables
    are initialized but without the fields that are accessed later.

    Args:
        workflow: The workflow dictionary
        var_fields_map: Dict mapping variable names to list of required fields
                       e.g. {"clientData": ["webauthn_encoded_result"], "userInfo": ["email", "name"]}

    Returns:
        Number of variables that were successfully updated
    """
    if not var_fields_map:
        return 0

    updated_count = 0
    for var_name, fields in var_fields_map.items():
        if update_variable_initialization_with_fields(workflow, var_name, fields):
            updated_count += 1

    return updated_count


def main(file_path):
    global AUTO_FIXES_APPLIED
    AUTO_FIXES_APPLIED = []

    # Security validation
    filename = validate_and_sanitize(file_path)

    data = None
    workflow = None

    # PRE-FIX: Auto-fix over-escaped backslashes in raw JSON BEFORE parsing
    print("Pre-validating raw JSON for escaping errors...")
    raw_text, escaping_fixes = fix_raw_json_escaping(file_path)

    if escaping_fixes > 0:
        log_auto_fix(
            f'Fixed {escaping_fixes} over-escaped quote(s) in raw JSON (e.g., \\\\" → \\")'
        )
        print(
            f"  ⚙️  AUTO-FIXED: Corrected {escaping_fixes} over-escaped backslash-quote sequence(s) in raw JSON"
        )

    try:
        with open(file_path, "r") as f:
            data = json.load(f)
        print(f"Successfully loaded JSON from {filename}")
    except Exception as e:
        print(f"❌ Failed to load Journey JSON file: {e}")
        sys.exit(1)

    if not isinstance(data, dict):
        print("❌ The journey JSON is not a valid dictionary.")
        sys.exit(1)

    # Apply journey-level fixes
    print("\nApplying journey-level fixes...")
    fix_journey_metadata(data)
    fix_journey_required_fields(data)

    # Extract workflow
    workflow = extract_workflow_from_journey(data)
    if not workflow:
        print("❌ Failed to extract workflow from journey JSON file")
        sys.exit(1)

    # Apply workflow-level fixes
    print("\nApplying workflow-level fixes...")
    fix_workflow_uuids(workflow)
    fix_loop_and_block_body(workflow)
    fix_loop_conditions(workflow)
    fix_condition_data_types(workflow)
    fix_set_variables_json_backticks(workflow)
    fix_link_types(workflow)
    fix_auth_pass_and_reject_metadata(workflow)
    fix_get_information_to_form(workflow)
    fix_strict_equality_operators(workflow)
    fix_information_node_expressions(workflow)

    # Save file if auto-fixes were applied
    if AUTO_FIXES_APPLIED:
        print(f"\n{'='*60}")
        print(f"📝 AUTO-FIXES APPLIED: {len(AUTO_FIXES_APPLIED)} fix(es)")
        print(f"{'='*60}")

        try:
            with open(file_path, "w") as f:
                json.dump(data, f, indent=2)
            print(f"✅ Saved updated journey to: {filename}")
        except Exception as e:
            print(f"⚠️  Failed to save file: {e}")
            sys.exit(1)

        print(f"\n💡 RECOMMENDATION: Run validators to verify all fixes:")
        print(f"   python validate_journey_structure.py {filename}")
        print(f"{'='*60}\n")

        print("✅ All auto-fixable errors have been corrected.")
    else:
        print("\n✅ No automatic fixes needed")

    sys.exit(0)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python journey_fixes.py <json_file_path>")
        sys.exit(1)
    file_path = sys.argv[1]

    if not os.path.isfile(file_path):
        print(f"Error: '{file_path}' is not a valid file path.")
        sys.exit(1)

    main(file_path)
