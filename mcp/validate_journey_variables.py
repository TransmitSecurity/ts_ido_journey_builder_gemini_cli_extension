#!/usr/bin/env python3
"""
Journey Variables Validator

Validates variable usage and scoping:
- Variables are defined before use
- Variables in loops are properly scoped
- Variable initialization with set_variables has proper structure
- Field access on variables matches their initialization
- Platform implicit variables (like 'error') usage

Auto-fixes:
- Adds uninitialized variables to set_variables nodes
"""

import json
import os
import re
import sys
from typing import Dict, List, Set, Tuple

from journey_validator_base import JourneyValidatorBase

# Import variable auto-fix functions from journey_fixes
try:
    import journey_fixes
except ImportError:
    journey_fixes = None


class JourneyVariablesValidator(JourneyValidatorBase):
    """Validates variable scoping and initialization."""

    def __init__(self, auto_fix: bool = True):
        super().__init__(auto_fix)
        self.auto_fixes_applied = []
        self.file_path = None

    def get_validator_name(self) -> str:
        return "Journey Variables Validation"

    def run_validations(self) -> None:
        """Run variable-specific validations with auto-fix support."""
        # Extract workflow first
        if not self.extract_workflow(required=True):
            return

        print("✓ Variable scoping validation")
        self.validate_variable_scoping()

        print("✓ Variable initialization validation")
        self.validate_variable_initialization()

        print("✓ Output variable initialization validation")
        self.validate_output_var_initialization()

    def validate_file(self, file_path: str) -> int:
        """Override to store file path for auto-fixes."""
        self.file_path = file_path
        return super().validate_file(file_path)

    def save_journey_with_fixes(self) -> bool:
        """Save the journey file with auto-fixes applied."""
        if not self.file_path or not self.journey_data:
            return False

        try:
            with open(self.file_path, "w") as f:
                json.dump(self.journey_data, f, indent=2)
            return True
        except Exception as e:
            print(f"⚠️  Failed to save auto-fixes: {e}")
            return False

    def extract_variable_references(self, expression_value: str) -> list:
        """Extract variable names from an expression string."""
        if not expression_value or not isinstance(expression_value, str):
            return []

        original = expression_value
        cleaned = expression_value

        # Handle template literals and information node expressions (${} interpolation)
        if "${" in cleaned:
            interpolation_pattern = r"\$\{([^}]+)\}"
            interpolations = re.findall(interpolation_pattern, cleaned)
            if interpolations:
                cleaned = " ".join(interpolations)
        elif cleaned.startswith("`") and cleaned.endswith("`"):
            # Template literal without ${} - static string
            return []
        else:
            if "${" not in expression_value and "`" not in expression_value:
                if not re.match(r"^[a-zA-Z_]", expression_value.strip()):
                    return []
            else:
                cleaned = re.sub(r"`[^`]*`", "", expression_value)

        # Remove strings
        cleaned = re.sub(r'"[^"]*"', "", cleaned)
        cleaned = re.sub(r"'[^']*'", "", cleaned)

        # Remove @-prefixed platform calls
        cleaned = re.sub(
            r"@[a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*(?:\([^)]*\))?)*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*",
            "",
            cleaned,
        )

        # Pattern to match variable references
        pattern = r"(?<!@)\b([a-zA-Z_][a-zA-Z0-9_]*)(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*"
        matches = re.findall(pattern, cleaned)

        # Filter out platform built-ins
        filtered_matches = []
        for match in matches:
            if f"@{match}" not in original:
                filtered_matches.append(match)

        # Filter out keywords
        keywords = {
            "true",
            "false",
            "null",
            "undefined",
            "True",
            "False",
            "None",
            "if",
            "else",
            "return",
            "var",
            "let",
            "const",
        }
        return [m for m in filtered_matches if m not in keywords]

    def extract_field_accesses(self, expression_value: str) -> list:
        """Extract field accesses from an expression string."""
        if not expression_value or not isinstance(expression_value, str):
            return []

        cleaned = expression_value

        # Handle template literals
        if "${" in cleaned:
            interpolation_pattern = r"\$\{([^}]+)\}"
            interpolations = re.findall(interpolation_pattern, cleaned)
            if interpolations:
                cleaned = " ".join(interpolations)
        elif cleaned.startswith("`") and cleaned.endswith("`"):
            cleaned = cleaned[1:-1]
        else:
            if "${" not in expression_value and "`" not in expression_value:
                if "." not in expression_value:
                    return []
            else:
                cleaned = re.sub(r"`[^`]*`", "", expression_value)

        # Remove strings
        cleaned = re.sub(r'"[^"]*"', "", cleaned)
        cleaned = re.sub(r"'[^']*'", "", cleaned)

        # Remove @-prefixed platform calls
        cleaned = re.sub(
            r"@[a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*(?:\([^)]*\))?",
            "",
            cleaned,
        )

        # Pattern to match variable.field accesses
        pattern = r"\b([a-zA-Z_][a-zA-Z0-9_]*)\.([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*)"
        matches = re.findall(pattern, cleaned)

        # Parse out individual field accesses
        field_accesses = []
        for var_name, field_chain in matches:
            if f"@{var_name}" not in expression_value:
                first_field = field_chain.split(".")[0]
                field_accesses.append((var_name, first_field))

        return field_accesses

    def find_variable_declarations_in_node(self, node: dict, node_id: str) -> set:
        """Find all variables declared in a node."""
        declared_vars = set()

        # Recursively search for all output_var fields anywhere in the node structure
        def find_output_vars(obj, path=""):
            """Recursively find all output_var fields in nested structures."""
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if key == "output_var" and isinstance(value, str):
                        declared_vars.add(value)
                    else:
                        find_output_vars(value, f"{path}.{key}" if path else key)
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    find_output_vars(item, f"{path}[{i}]")

        find_output_vars(node)

        # Check for set_variables action
        if node.get("type") == "action" and "action" in node:
            action = node["action"]
            if action.get("type") == "set_variables" and "variables" in action:
                for var in action["variables"]:
                    if "name" in var:
                        declared_vars.add(var["name"])

            # Check for forms with var_name
            if "var_name" in action:
                declared_vars.add(action["var_name"])

        # Check for loop variables
        if node.get("type") == "loop" and "variables" in node:
            for var in node["variables"]:
                if "name" in var:
                    declared_vars.add(var["name"])

        return declared_vars

    def find_variable_references_in_node(self, node: dict, node_id: str) -> set:
        """Find all variables referenced (used) in a node."""
        referenced_vars = set()

        # Check if this is an invoke_idp node - skip provider_config validation
        node_type = node.get("type")
        if node_type == "action" and "action" in node:
            action_type = node.get("action", {}).get("type")
            is_invoke_idp = action_type == "invoke_idp"
        else:
            is_invoke_idp = False

        def extract_from_dict(d, parent_key=None):
            """Recursively extract variable references from a dictionary."""
            if isinstance(d, dict):
                # Skip form_schema, data_json_schema, and provider_config
                if parent_key in ["form_schema", "data_json_schema"]:
                    return
                if is_invoke_idp and parent_key == "provider_config":
                    return

                # Check for expression values
                if d.get("type") == "expression" and "value" in d:
                    value_str = str(d["value"])

                    # Skip if this looks like a JSON schema
                    schema_indicators = [
                        '"type":',
                        '"properties":',
                        '"$schema":',
                        '"format":',
                    ]
                    if not any(
                        indicator in value_str for indicator in schema_indicators
                    ):
                        vars_in_expr = self.extract_variable_references(value_str)
                        referenced_vars.update(vars_in_expr)

                # Recurse into nested structures
                for key, value in d.items():
                    if isinstance(value, dict):
                        extract_from_dict(value, parent_key=key)
                    elif isinstance(value, list):
                        for item in value:
                            if isinstance(item, dict):
                                extract_from_dict(item, parent_key=key)

        extract_from_dict(node)
        return referenced_vars

    def validate_variable_scoping(self) -> None:
        """Validate that variables are used within their proper scope."""
        # Try auto-fix first if enabled
        if self.auto_fix and self.file_path:
            self._validate_variable_scoping_with_autofix()
        else:
            self._validate_variable_scoping_impl()

    def _validate_variable_scoping_with_autofix(self) -> None:
        """Run variable scoping validation with auto-fix support."""
        # First pass: run validation and collect issues
        initial_error_count = len(self.error_messages)
        uninitialized_vars = self._validate_variable_scoping_impl()

        if not uninitialized_vars:
            return  # No issues to auto-fix

        # Print warnings for variables that will be auto-fixed
        unique_vars = set()
        for var_name, node_id, error_type in uninitialized_vars:
            if error_type in ["undefined", "error_implicit"]:
                unique_vars.add(var_name)

        if not unique_vars:
            return  # No auto-fixable issues

        print(
            f"\n⚠️  Found {len(unique_vars)} uninitialized variable(s): {sorted(unique_vars)}"
        )
        print("  Attempting to auto-fix by adding to set_variables node...")

        # Check if journey_fixes module is available
        if journey_fixes is None:
            print("  ❌ journey_fixes module not available, cannot auto-fix")
            return

        # Use journey_fixes to add uninitialized variables
        added_count = journey_fixes.auto_fix_uninitialized_variables(
            self.workflow, sorted(unique_vars)
        )

        if added_count == 0:
            print("  ❌ Could not auto-fix variables")
            return

        # Save the file
        if self.save_journey_with_fixes():
            print(f"  ✅ Auto-fixed {len(unique_vars)} variable(s)")

            # Reload the file and re-run validation
            print("  Re-validating after auto-fixes...")
            if not self.load_journey_file(self.file_path):
                print("  ❌ Failed to reload file after auto-fix")
                return

            if not self.extract_workflow(required=True):
                print("  ❌ Failed to extract workflow after auto-fix")
                return

            # Clear previous errors and re-run validation
            self.error_messages = self.error_messages[:initial_error_count]
            uninitialized_vars_after = self._validate_variable_scoping_impl()

            if not uninitialized_vars_after:
                print("  ✅ All variable scoping issues resolved by auto-fix")
            else:
                print(
                    f"  ⚠️  {len(uninitialized_vars_after)} issue(s) remain after auto-fix"
                )
        else:
            print("  ❌ Failed to save auto-fixes")

    def _validate_variable_scoping_impl(self) -> List[Tuple[str, str, str]]:
        """
        Implementation of variable scoping validation.
        Returns: List of (var_name, node_id, error_type) tuples for uninitialized vars.
        """
        # Get platform implicit variables from constants
        platform_implicit_vars = self.constants.get("platform_implicit_variables", {})
        PLATFORM_IMPLICIT_VARS = set(platform_implicit_vars.keys())

        uninitialized_vars = []  # Track vars that could be auto-fixed

        # Track nodes that are inside loops or blocks
        nodes_in_loops = {}  # node_id -> loop_node_id
        nodes_in_blocks = {}  # node_id -> block_node_id

        def mark_nodes_in_scope(
            node_id: str, loop_id: str = None, block_id: str = None, visited: set = None
        ):
            """Recursively mark which nodes are inside loops/blocks."""
            if visited is None:
                visited = set()

            if node_id in visited or node_id not in self.workflow["nodes"]:
                return

            visited.add(node_id)
            node = self.workflow["nodes"][node_id]

            # Mark current node's scope
            if loop_id:
                nodes_in_loops[node_id] = loop_id
            if block_id:
                nodes_in_blocks[node_id] = block_id

            # Handle loop body
            if (
                node.get("type") == "loop"
                and "loop_body" in node
                and "id" in node["loop_body"]
            ):
                body_id = node["loop_body"]["id"]
                mark_nodes_in_scope(
                    body_id, loop_id=node_id, block_id=block_id, visited=visited
                )

            # Handle block body
            elif (
                node.get("type") == "block"
                and "block" in node
                and "id" in node["block"]
            ):
                body_id = node["block"]["id"]
                mark_nodes_in_scope(
                    body_id, loop_id=loop_id, block_id=node_id, visited=visited
                )

            # Follow links
            if "links" in node:
                for link in node["links"]:
                    if "target" in link and link["target"]:
                        target_id = link["target"]

                        # If target is outside current loop body, don't propagate loop scope
                        if loop_id and target_id not in visited:
                            loop_body_nodes = set()
                            collect_body_nodes(loop_id, loop_body_nodes)
                            if target_id not in loop_body_nodes:
                                # Exiting loop
                                mark_nodes_in_scope(
                                    target_id,
                                    loop_id=None,
                                    block_id=block_id,
                                    visited=visited,
                                )
                                continue

                        mark_nodes_in_scope(
                            target_id,
                            loop_id=loop_id,
                            block_id=block_id,
                            visited=visited,
                        )

        def collect_body_nodes(
            loop_or_block_id: str, body_nodes: set, visited: set = None
        ):
            """Collect all nodes that are part of a loop/block body."""
            if visited is None:
                visited = set()

            if (
                loop_or_block_id in visited
                or loop_or_block_id not in self.workflow["nodes"]
            ):
                return

            visited.add(loop_or_block_id)
            node = self.workflow["nodes"][loop_or_block_id]

            if (
                node.get("type") == "loop"
                and "loop_body" in node
                and "id" in node["loop_body"]
            ):
                body_id = node["loop_body"]["id"]
                body_nodes.add(body_id)
                collect_loop_body_nodes(body_id, body_nodes, visited)
            elif (
                node.get("type") == "block"
                and "block" in node
                and "id" in node["block"]
            ):
                body_id = node["block"]["id"]
                body_nodes.add(body_id)
                collect_loop_body_nodes(body_id, body_nodes, visited)

        def collect_loop_body_nodes(node_id: str, body_nodes: set, visited: set):
            """Recursively collect nodes in a loop body."""
            if node_id in visited or node_id not in self.workflow["nodes"]:
                return

            visited.add(node_id)
            body_nodes.add(node_id)
            node = self.workflow["nodes"][node_id]

            if "links" in node:
                for link in node["links"]:
                    if "target" in link and link["target"]:
                        collect_loop_body_nodes(link["target"], body_nodes, visited)

        # Mark all nodes with their scope
        if "head" in self.workflow and self.workflow["head"] in self.workflow["nodes"]:
            mark_nodes_in_scope(self.workflow["head"])

        # Track variable declarations and check references
        global_vars = set()
        loop_vars = {}  # loop_id -> set of variables

        # First pass: collect all variable declarations
        for node_id, node in self.workflow["nodes"].items():
            declared = self.find_variable_declarations_in_node(node, node_id)

            if node_id in nodes_in_loops:
                loop_id = nodes_in_loops[node_id]
                if loop_id not in loop_vars:
                    loop_vars[loop_id] = set()
                loop_vars[loop_id].update(declared)
            else:
                global_vars.update(declared)

        # Second pass: check variable references
        for node_id, node in self.workflow["nodes"].items():
            referenced = self.find_variable_references_in_node(node, node_id)

            # Determine which variables are in scope at this node
            vars_in_scope = global_vars.copy()

            # If node is in a loop, add loop-scoped variables
            if node_id in nodes_in_loops:
                loop_id = nodes_in_loops[node_id]
                if loop_id in loop_vars:
                    vars_in_scope.update(loop_vars[loop_id])

            # Check each referenced variable
            for var_name in referenced:
                if var_name not in vars_in_scope:
                    # Check if it's a platform implicit variable
                    if var_name in PLATFORM_IMPLICIT_VARS:
                        if var_name == "error":
                            # Error variable - can be auto-fixed
                            uninitialized_vars.append(
                                (var_name, node_id, "error_implicit")
                            )
                            self.error_messages.append(
                                f"Node {node_id} references implicit variable 'error' which is NOT declared. "
                                f"The 'error' variable is provided by the platform only after certain node executions "
                                f"(typically in failure branches). Using 'error' in nodes reachable from multiple paths "
                                f"may cause runtime errors if it's not defined.\n"
                                f"\n"
                                f"  🔧 RECOMMENDED FIXES:\n"
                                f"  1. Initialize 'error' with set_variables before the journey:\n"
                                f'     {{"name": "error", "value": "null"}}\n'
                                f"  2. Use error checking in your expression:\n"
                                f"     `Status: ${{typeof error !== 'undefined' && error ? 'Failed' : 'Success'}}`\n"
                                f"  3. Restructure so this node is only reachable from failure branches."
                            )
                        else:
                            # Other platform implicit - can't auto-fix
                            self.error_messages.append(
                                f"Node {node_id} references implicit platform variable '{var_name}' which is NOT declared. "
                                f"This variable may not be available in all execution contexts."
                            )
                        continue

                    # Variable is not in scope
                    if node_id in nodes_in_loops:
                        # Can't easily auto-fix loop scope issues
                        self.error_messages.append(
                            f"Node {node_id} references variable '{var_name}' which is not in scope. "
                            f"Variables created inside loops must be initialized with set_variables before the loop "
                            f"to be accessible outside the loop."
                        )
                    else:
                        # Check if variable was declared in a loop
                        declared_in_loop = False
                        for loop_id, loop_var_set in loop_vars.items():
                            if var_name in loop_var_set:
                                declared_in_loop = True
                                # Can't easily auto-fix loop scope issues
                                self.error_messages.append(
                                    f"Node {node_id} (outside loop) references variable '{var_name}' which was declared "
                                    f"inside loop {loop_id}. Variables created with output_var inside loops are not "
                                    f"accessible outside the loop. Initialize the variable with set_variables before the loop."
                                )
                                break

                        if not declared_in_loop:
                            # This can be auto-fixed!
                            uninitialized_vars.append((var_name, node_id, "undefined"))
                            self.error_messages.append(
                                f"Node {node_id} references undefined variable '{var_name}'."
                            )

        return uninitialized_vars

    def validate_variable_initialization(self) -> None:
        """Validate that variables initialized with set_variables have all accessed fields defined."""
        # Try auto-fix first if enabled
        if self.auto_fix and self.file_path:
            self._validate_variable_initialization_with_autofix()
        else:
            self._validate_variable_initialization_impl()

    def _validate_variable_initialization_with_autofix(self) -> None:
        """Run variable initialization validation with auto-fix support."""
        # First pass: run validation and collect issues
        initial_error_count = len(self.error_messages)
        var_fields_to_fix = self._validate_variable_initialization_impl()

        if not var_fields_to_fix:
            return  # No issues to auto-fix

        print(
            f"\n⚠️  Found {len(var_fields_to_fix)} variable(s) with missing field initialization: {sorted(var_fields_to_fix.keys())}"
        )
        print(
            "  Attempting to auto-fix by adding fields to variable initializations..."
        )

        # Check if journey_fixes module is available
        if journey_fixes is None:
            print("  ❌ journey_fixes module not available, cannot auto-fix")
            return

        # Use journey_fixes to update variable initializations
        updated_count = journey_fixes.auto_fix_variable_field_initialization(
            self.workflow, var_fields_to_fix
        )

        if updated_count == 0:
            print("  ❌ Could not auto-fix variable field initializations")
            return

        # Save the file
        if self.save_journey_with_fixes():
            print(f"  ✅ Auto-fixed {updated_count} variable initialization(s)")

            # Reload the file and re-run validation
            print("  Re-validating after auto-fixes...")
            if not self.load_journey_file(self.file_path):
                print("  ❌ Failed to reload file after auto-fix")
                return

            if not self.extract_workflow(required=True):
                print("  ❌ Failed to extract workflow after auto-fix")
                return

            # Clear previous errors and re-run validation
            self.error_messages = self.error_messages[:initial_error_count]
            var_fields_to_fix_after = self._validate_variable_initialization_impl()

            if not var_fields_to_fix_after:
                print("  ✅ All variable initialization issues resolved by auto-fix")
            else:
                print(
                    f"  ⚠️  {len(var_fields_to_fix_after)} issue(s) remain after auto-fix"
                )
        else:
            print("  ❌ Failed to save auto-fixes")

    def _validate_variable_initialization_impl(self) -> dict:
        """
        Implementation of variable initialization validation.
        Returns: Dict mapping var_name to list of missing fields that could be auto-fixed.
        """
        var_fields_to_fix = {}  # var_name -> [missing_fields]

        # Track variables initialized with set_variables and their structure
        initialized_vars = {}  # var_name -> {field1, field2, ...}

        # Track variables created via output_var (exclude form nodes)
        output_var_variables = set()

        # First pass: find all variable declarations
        for node_id, node in self.workflow["nodes"].items():
            # Check if this is a form node
            is_form_node = False
            if node.get("type") == "action" and "action" in node:
                action = node["action"]
                if action.get("type") == "form":
                    is_form_node = True

            # Recursively find all output_var declarations (skip form nodes)
            if not is_form_node:

                def find_output_vars(obj):
                    """Recursively find all output_var fields in nested structures."""
                    if isinstance(obj, dict):
                        for key, value in obj.items():
                            if key == "output_var" and isinstance(value, str):
                                output_var_variables.add(value)
                            else:
                                find_output_vars(value)
                    elif isinstance(obj, list):
                        for item in obj:
                            find_output_vars(item)

                find_output_vars(node)

            # Track set_variables and parse their structure
            if node.get("type") == "action" and "action" in node:
                if (
                    node["action"].get("type") == "set_variables"
                    and "variables" in node["action"]
                ):
                    for var in node["action"]["variables"]:
                        if "name" in var and "value" in var:
                            var_name = var["name"]
                            var_value = var["value"]

                            # Try to parse the value if it's an expression with JSON structure
                            if (
                                isinstance(var_value, dict)
                                and var_value.get("type") == "expression"
                            ):
                                value_str = var_value.get("value", "")

                                try:
                                    # Handle backtick-wrapped JSON
                                    if value_str.startswith("`") and value_str.endswith(
                                        "`"
                                    ):
                                        value_str = value_str[1:-1]

                                    parsed = json.loads(value_str)
                                    if isinstance(parsed, dict):
                                        # Store the initialized fields
                                        initialized_vars[var_name] = set(parsed.keys())
                                    else:
                                        # Not an object, so no fields
                                        initialized_vars[var_name] = set()
                                except (json.JSONDecodeError, ValueError):
                                    # Couldn't parse, treat as empty
                                    if value_str.strip() in ["{}", "`{}`", '"{}"']:
                                        initialized_vars[var_name] = set()

        # Second pass: find all field accesses and check if they were initialized
        accessed_fields = {}  # var_name -> {(field, node_id), ...}

        def scan_node_for_field_accesses(node: dict, node_id: str):
            """Recursively scan node for field accesses."""
            if isinstance(node, dict):
                # Check for expression values
                if node.get("type") == "expression" and "value" in node:
                    field_refs = self.extract_field_accesses(str(node["value"]))
                    for var_name, field in field_refs:
                        if var_name not in accessed_fields:
                            accessed_fields[var_name] = set()
                        accessed_fields[var_name].add((field, node_id))

                # Recurse into nested structures
                for value in node.values():
                    if isinstance(value, dict):
                        scan_node_for_field_accesses(value, node_id)
                    elif isinstance(value, list):
                        for item in value:
                            if isinstance(item, dict):
                                scan_node_for_field_accesses(item, node_id)

        for node_id, node in self.workflow["nodes"].items():
            scan_node_for_field_accesses(node, node_id)

        # Check if accessed fields were initialized
        for var_name, fields_and_nodes in accessed_fields.items():
            if var_name in initialized_vars:
                # Variable was explicitly initialized with set_variables
                initialized_fields = initialized_vars[var_name]
                is_also_output_var = var_name in output_var_variables

                # If initialized as empty object but fields are accessed, warn
                if not initialized_fields and fields_and_nodes:
                    accessed_fields_list = sorted(
                        set(field for field, _ in fields_and_nodes)
                    )
                    nodes_with_access = sorted(
                        set(node_id for _, node_id in fields_and_nodes)
                    )

                    # Track for auto-fix
                    var_fields_to_fix[var_name] = accessed_fields_list

                    if is_also_output_var:
                        self.error_messages.append(
                            f"Variable '{var_name}' is initialized as empty object {{}} AND used as output_var, "
                            f"but fields {accessed_fields_list} are accessed in nodes {nodes_with_access}.\n"
                            f"\n"
                            f"  🔧 FIX: Initialize with proper nested structure in set_variables:\n"
                            f'     {{"name": "{var_name}", "value": "{{\\"field\\": \\"\\"}}"}} \n'
                            f"     (Include all accessed fields: {accessed_fields_list})"
                        )
                    else:
                        self.error_messages.append(
                            f"Variable '{var_name}' is initialized as empty object {{}}, "
                            f"but fields {accessed_fields_list} are accessed in nodes {nodes_with_access}. "
                            f'Initialize with proper structure: {{"name": "{var_name}", "value": '
                            f'"{{\\"{accessed_fields_list[0]}\\": \\"\\"}}"}} (include all accessed fields)'
                        )
                else:
                    # Check if all accessed fields were initialized
                    missing_fields = []
                    for field, node_id in fields_and_nodes:
                        if field not in initialized_fields:
                            missing_fields.append(field)
                            if is_also_output_var:
                                self.error_messages.append(
                                    f"Variable '{var_name}' does not have field '{field}' initialized, "
                                    f"but it is accessed in node {node_id}. This variable is ALSO used as output_var.\n"
                                    f"\n"
                                    f"  🔧 FIX: Initialize with nested structure that includes '{field}'"
                                )
                            else:
                                self.error_messages.append(
                                    f"Variable '{var_name}' does not have field '{field}' initialized, "
                                    f"but it is accessed in node {node_id}. "
                                    f'Initialize with: {{"name": "{var_name}", "value": "{{{{\\"{field}\\": \\"\\"}}}}"}}'
                                )

                    # Track for auto-fix if there are missing fields
                    if missing_fields:
                        var_fields_to_fix[var_name] = sorted(set(missing_fields))

            elif var_name in output_var_variables:
                # Variable created via output_var without initialization
                accessed_fields_list = sorted(
                    set(field for field, _ in fields_and_nodes)
                )
                nodes_with_access = sorted(
                    set(node_id for _, node_id in fields_and_nodes)
                )

                # Track for auto-fix
                var_fields_to_fix[var_name] = accessed_fields_list

                self.error_messages.append(
                    f"Variable '{var_name}' is created via output_var but fields {accessed_fields_list} "
                    f"are accessed in nodes {nodes_with_access} without explicit initialization. "
                    f"Platform nodes may not return the expected field structure.\n"
                    f"\n"
                    f"  🔧 FIX: Initialize '{var_name}' with set_variables BEFORE accessing its fields:\n"
                    f'  {{"name": "{var_name}", "value": "{{\\"'
                    + '\\": \\"\\", \\"'.join(accessed_fields_list)
                    + '\\": \\"\\"}}"}}'
                )

        return var_fields_to_fix

    def validate_output_var_initialization(self) -> None:
        """Validate that variables used in output_var are initialized before use."""
        # Try auto-fix first if enabled
        if self.auto_fix and self.file_path:
            self._validate_output_var_initialization_with_autofix()
        else:
            self._validate_output_var_initialization_impl()

    def _validate_output_var_initialization_impl(self) -> List[Tuple[str, str]]:
        """
        Implementation of output_var initialization validation.
        Returns: List of (var_name, node_id) tuples for uninitialized vars.
        """
        uninitialized_output_vars = []

        # Track which variables are initialized in set_variables
        initialized_vars = set()

        # Track which variables are used as output_var (excluding form nodes)
        output_var_usage = {}  # var_name -> (node_id, is_form)

        # Process nodes in execution order (BFS from head)
        visited = set()
        queue = []

        if "head" in self.workflow and self.workflow["head"] in self.workflow["nodes"]:
            queue.append(self.workflow["head"])

        while queue:
            node_id = queue.pop(0)
            if node_id in visited or node_id not in self.workflow["nodes"]:
                continue

            visited.add(node_id)
            node = self.workflow["nodes"][node_id]

            # Check if this node has set_variables - track initialized vars
            if node.get("type") == "action" and "action" in node:
                action = node["action"]
                if action.get("type") == "set_variables" and "variables" in action:
                    for var in action["variables"]:
                        if "name" in var:
                            initialized_vars.add(var["name"])

            # Check if this is a form node
            is_form_node = False
            if node.get("type") == "action" and "action" in node:
                if node["action"].get("type") == "form":
                    is_form_node = True

            # Find all output_var usages in this node
            def find_output_var_usage(obj):
                """Recursively find output_var usage."""
                if isinstance(obj, dict):
                    for key, value in obj.items():
                        if key == "output_var" and isinstance(value, str):
                            if value not in output_var_usage:
                                output_var_usage[value] = (node_id, is_form_node)
                        else:
                            find_output_var_usage(value)
                elif isinstance(obj, list):
                    for item in obj:
                        find_output_var_usage(item)

            find_output_var_usage(node)

            # Add children to queue
            if "links" in node:
                for link in node["links"]:
                    if "target" in link and link["target"]:
                        queue.append(link["target"])

            # Handle loop body
            if (
                node.get("type") == "loop"
                and "loop_body" in node
                and "id" in node["loop_body"]
            ):
                queue.append(node["loop_body"]["id"])

            # Handle block body
            if (
                node.get("type") == "block"
                and "block" in node
                and "id" in node["block"]
            ):
                queue.append(node["block"]["id"])

        # Check for output_var usage without initialization
        for var_name, (node_id, is_form) in output_var_usage.items():
            # Skip form nodes - they initialize via var_name
            if is_form:
                continue

            if var_name not in initialized_vars:
                uninitialized_output_vars.append((var_name, node_id))
                self.error_messages.append(
                    f"Variable '{var_name}' is used as output_var in node {node_id} but was not initialized.\n"
                    f"\n"
                    f"  🔧 FIX: Initialize '{var_name}' with set_variables BEFORE it's used as output_var:\n"
                    f"  Add to the initial set_variables node:\n"
                    f'  {{"name": "{var_name}", "value": "null"}}\n'
                    f"\n"
                    f"  Platform nodes that set output_var should overwrite pre-initialized variables to avoid runtime errors."
                )

        return uninitialized_output_vars

    def _validate_output_var_initialization_with_autofix(self) -> None:
        """Run output_var initialization validation with auto-fix support."""
        # First pass: run validation and collect issues
        initial_error_count = len(self.error_messages)
        uninitialized_vars = self._validate_output_var_initialization_impl()

        if not uninitialized_vars:
            return  # No issues to auto-fix

        unique_vars = set(var_name for var_name, _ in uninitialized_vars)

        print(
            f"\n⚠️  Found {len(unique_vars)} uninitialized output_var variable(s): {sorted(unique_vars)}"
        )
        print("  Attempting to auto-fix by adding to set_variables node...")

        # Check if journey_fixes module is available
        if journey_fixes is None:
            print("  ❌ journey_fixes module not available, cannot auto-fix")
            return

        # Use journey_fixes to add uninitialized variables
        added_count = journey_fixes.auto_fix_uninitialized_variables(
            self.workflow, sorted(unique_vars)
        )

        if added_count == 0:
            print("  ❌ Could not auto-fix variables")
            return

        # Save the file
        if self.save_journey_with_fixes():
            print(f"  ✅ Auto-fixed {len(unique_vars)} variable(s)")

            # Reload the file and re-run validation
            print("  Re-validating after auto-fixes...")
            if not self.load_journey_file(self.file_path):
                print("  ❌ Failed to reload file after auto-fix")
                return

            if not self.extract_workflow(required=True):
                print("  ❌ Failed to extract workflow after auto-fix")
                return

            # Clear previous errors and re-run validation
            self.error_messages = self.error_messages[:initial_error_count]
            uninitialized_vars_after = self._validate_output_var_initialization_impl()

            if not uninitialized_vars_after:
                print("  ✅ All output_var initialization issues resolved by auto-fix")
            else:
                print(
                    f"  ⚠️  {len(uninitialized_vars_after)} issue(s) remain after auto-fix"
                )
        else:
            print("  ❌ Failed to save auto-fixes")


if __name__ == "__main__":
    JourneyVariablesValidator.main()
