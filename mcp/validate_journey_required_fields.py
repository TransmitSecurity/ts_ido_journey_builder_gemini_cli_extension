#!/usr/bin/env python3
"""
Journey Required Fields Validator

Validates that nodes have all required fields based on their type:
- Platform node required fields (user_identifier, password, etc.)
- Action node required fields (text, button_text, data, etc.)
- Field type validation (plain strings vs expressions)
- Form schema structure
- Condition node structure
- JSON data format
"""

import json
import re

from journey_validator_base import JourneyValidatorBase


class JourneyRequiredFieldsValidator(JourneyValidatorBase):
    """Validates node-level required fields."""

    def get_validator_name(self) -> str:
        return "Journey Required Fields Validation"

    def run_validations(self) -> None:
        """Run required fields validations."""
        # Extract workflow first
        if not self.extract_workflow(required=True):
            return

        print("✓ Platform node required fields")
        self.validate_platform_node_fields()

        print("✓ Action node required fields")
        self.validate_action_specific_fields()

        print("✓ Field type validation (plain strings vs expressions)")
        self.validate_field_types()

        print("✓ Form schema validation")
        self.validate_form_schemas()

        print("✓ Condition node structure")
        self.validate_condition_data_types()

        print("✓ JSON data format")
        self.validate_json_data_format()

    def is_field_empty(self, field_value) -> bool:
        """Check if a field value is empty or contains only whitespace."""
        if field_value is None:
            return True
        if isinstance(field_value, str):
            return field_value.strip() == ""
        if isinstance(field_value, dict):
            # For expression objects, check the value field
            if field_value.get("type") == "expression":
                value = field_value.get("value", "")
                if isinstance(value, str):
                    # Remove backticks if present
                    cleaned = value.strip("`").strip()
                    return cleaned == ""
                return value is None or value == ""
        return False

    def validate_platform_node_fields(self) -> None:
        """Validate platform-specific node field requirements."""
        for node_id, node_data in self.workflow["nodes"].items():
            if not isinstance(node_data, dict):
                continue

            node_type = node_data.get("type", "")

            # Check for deprecated node types using node_defs
            if node_type in self.node_defs:
                node_def = self.node_defs[node_type]
                if node_def.get("deprecated", False):
                    replacement = node_def.get("replacement", "")
                    self.error_messages.append(
                        f"Node '{node_id}' uses deprecated node type '{node_type}'. "
                        f"This node type is no longer supported. Use '{replacement}' instead."
                    )
                    continue

            # Get required fields from node_defs
            if node_type in self.node_defs:
                node_def = self.node_defs[node_type]
                required_fields = node_def.get("required_fields", {})

                # Special case: at_least_one_of (e.g., transmit_platform_create_user)
                if "at_least_one_of" in node_def:
                    at_least_one = node_def["at_least_one_of"]
                    has_any = any(field in node_data for field in at_least_one)
                    if not has_any:
                        self.error_messages.append(
                            f"Node {node_id} ({node_type}) must have at least one of: {', '.join(at_least_one)}"
                        )

                # Check for required fields
                for field, field_type in required_fields.items():
                    if field not in node_data:
                        self.error_messages.append(
                            f"Node {node_id} ({node_type}) is missing required field: {field}"
                        )
                    else:
                        # Field exists, check if it has a non-empty value
                        field_value = node_data[field]
                        if self.is_field_empty(field_value):
                            error_msg = (
                                f"Node {node_id} ({node_type}) has empty value for required field '{field}'. "
                                f"This field must contain a non-empty value for the journey to run.\n"
                            )
                            # Add specific guidance for common fields
                            if field == "phone":
                                error_msg += (
                                    f'  Example: "phone": {{"type": "expression", "value": "userProfile.phone"}}\n'
                                    f'  or: "phone": {{"type": "expression", "value": "+1234567890"}}'
                                )
                            elif field == "email":
                                error_msg += f'  Example: "email": {{"type": "expression", "value": "userProfile.email"}}'
                            elif field == "user_identifier":
                                error_msg += f'  Example: "user_identifier": {{"type": "expression", "value": "emailData.email"}}'
                            self.error_messages.append(error_msg)

    def validate_action_specific_fields(self) -> None:
        """Validate that action nodes have required fields for their specific action type."""
        for node_id, node in self.workflow["nodes"].items():
            if node.get("type") == "action" and "action" in node:
                action = node["action"]
                action_type = action.get("type")

                # Get field requirements from node_defs
                if action_type in self.node_defs:
                    node_def = self.node_defs[action_type]
                    required_fields = node_def.get("required_fields", {})
                    optional_fields = node_def.get("optional_fields", {})

                    # Check for missing required fields
                    for field in required_fields.keys():
                        if field not in action:
                            self.error_messages.append(
                                f"Node {node_id} (action type '{action_type}') is missing required field '{field}'. "
                                f"Action type '{action_type}' requires: {', '.join(required_fields.keys())}"
                            )

                    # Validate specific field types for certain actions
                    if action_type == "events_enrichment" and "data" in action:
                        data_field = action["data"]
                        if not isinstance(data_field, list):
                            self.error_messages.append(
                                f"Node {node_id} (action type 'events_enrichment') has 'data' field that is not an array. "
                                f"events_enrichment requires 'data' to be an array of key/value pairs: "
                                f'[{{"key": "field_name", "value": {{"type": "expression", "value": "..."}}}}]'
                            )
                        else:
                            # Validate each element in the array
                            for idx, item in enumerate(data_field):
                                if not isinstance(item, dict):
                                    self.error_messages.append(
                                        f"Node {node_id} (action type 'events_enrichment') data[{idx}] is not an object. "
                                        f"Each data item must have 'key' and 'value' fields."
                                    )
                                    continue

                                if "key" not in item:
                                    self.error_messages.append(
                                        f"Node {node_id} (action type 'events_enrichment') data[{idx}] is missing 'key' field. "
                                        f"Use 'key' (not 'name') for the field name."
                                    )

                                if "value" not in item:
                                    self.error_messages.append(
                                        f"Node {node_id} (action type 'events_enrichment') data[{idx}] is missing 'value' field."
                                    )
                                elif isinstance(item["value"], dict):
                                    # Value should be an expression object
                                    if item["value"].get("type") != "expression":
                                        self.error_messages.append(
                                            f"Node {node_id} (action type 'events_enrichment') data[{idx}] value should be an expression object: "
                                            f'{{"type": "expression", "value": "..."}}'
                                        )

                    # Other data-based actions use expression object format
                    elif action_type in [
                        "json_data",
                        "sdk_data",
                        "custom_activity_log",
                        "custom_session_data",
                        "custom_token_enrichment",
                    ]:
                        if "data" in action:
                            data_field = action["data"]
                            if not isinstance(data_field, dict):
                                self.error_messages.append(
                                    f"Node {node_id} (action type '{action_type}') has 'data' field that is not an object. "
                                    f"Expected an expression object with 'type' and 'value' fields."
                                )
                            elif data_field.get("type") != "expression":
                                self.error_messages.append(
                                    f"Node {node_id} (action type '{action_type}') has 'data' field without type='expression'. "
                                    f'The \'data\' field should be: {{"type": "expression", "value": "..."}}'
                                )

    def validate_field_types(self) -> None:
        """Validate that certain fields use plain strings instead of expression objects."""
        for node_id, node in self.workflow["nodes"].items():
            node_type = node.get("type")

            # For action nodes, check the action type
            if node_type == "action" and "action" in node:
                action_type = node["action"].get("type")

                # Get field requirements from node_defs
                if action_type in self.node_defs:
                    node_def = self.node_defs[action_type]
                    required_fields = node_def.get("required_fields", {})

                    check_location = node["action"]
                    # Check all required fields for type mismatches
                    for field_name, expected_type in required_fields.items():
                        if field_name in check_location:
                            field_value = check_location[field_name]

                            # Check if field should be plain string but is an expression
                            if (
                                expected_type == "string"
                                and isinstance(field_value, dict)
                                and field_value.get("type") == "expression"
                            ):
                                actual_value = field_value.get("value", "")
                                clean_value = (
                                    actual_value.strip("`")
                                    if isinstance(actual_value, str)
                                    else actual_value
                                )
                                self.error_messages.append(
                                    f"Node {node_id} ({action_type}) field '{field_name}' must be a plain JSON string, "
                                    f"not an expression object. Change from:\n"
                                    f'  "{field_name}": {{"type": "expression", "value": "{actual_value}"}}\n'
                                    f"to:\n"
                                    f'  "{field_name}": "{clean_value}"'
                                )

    def validate_form_schemas(self) -> None:
        """Validate all form_schema and data_json_schema in the journey."""
        for node_id, node in self.workflow["nodes"].items():
            # Check for form_schema in action nodes
            if node.get("type") == "action" and "action" in node:
                action = node["action"]

                # Check form_schema
                if "form_schema" in action:
                    if (
                        isinstance(action["form_schema"], dict)
                        and "value" in action["form_schema"]
                    ):
                        schema_value = action["form_schema"]["value"]
                        self.validate_form_schema(schema_value, node_id, "form_schema")

                        # Additional checks for get_information forms
                        if action.get("metadata", {}).get("type") == "get_information":
                            if "output_var" not in node:
                                self.error_messages.append(
                                    f"Node {node_id} is a get_information form but is missing top-level 'output_var' field."
                                )
                            if "app_data" not in action:
                                self.error_messages.append(
                                    f"Node {node_id} is a get_information form but is missing 'app_data' field."
                                )
                            else:
                                # Validate app_data structure
                                app_data = action["app_data"]
                                if isinstance(app_data, dict):
                                    # If it's a plain empty object, that's invalid
                                    if app_data == {}:
                                        self.error_messages.append(
                                            f"Node {node_id} is a get_information form with invalid 'app_data': {{}}\n"
                                            f"  Platform expects 'app_data' to be an expression object.\n"
                                            f'  ✅ CORRECT: "app_data": {{"type": "expression", "value": "{{}}"}}\n'
                                            f'  ❌ INCORRECT: "app_data": {{}}'
                                        )
                                    # If it's a dict but not an expression object, check if it should be
                                    elif "type" not in app_data:
                                        self.error_messages.append(
                                            f"Node {node_id} is a get_information form with 'app_data' object missing 'type' field.\n"
                                            f"  Platform expects expression format: "
                                            f'{{"type": "expression", "value": "..."}}'
                                        )
                            if "strings" not in node:
                                self.error_messages.append(
                                    f"Node {node_id} is a get_information form but is missing top-level 'strings' array."
                                )

                # Check data_json_schema in login_form links
                if (
                    action.get("metadata", {}).get("type") == "login_form"
                    and "links" in node
                ):
                    for link in node["links"]:
                        if "data_json_schema" in link:
                            if (
                                isinstance(link["data_json_schema"], dict)
                                and "value" in link["data_json_schema"]
                            ):
                                schema_value = link["data_json_schema"]["value"]
                                if schema_value and schema_value.strip():
                                    self.validate_form_schema(
                                        schema_value,
                                        node_id,
                                        f"data_json_schema (link: {link.get('name', 'unknown')})",
                                    )

    def validate_form_schema(
        self, schema_value: str, node_id: str, schema_type: str
    ) -> None:
        """Validate form_schema or data_json_schema formatting and content."""
        # Check for empty or placeholder schemas
        if not schema_value or schema_value.strip() in ["", "...", "{}", "[]", "``"]:
            self.error_messages.append(
                f"Node {node_id} has an empty or placeholder {schema_type}. Must contain valid field definitions."
            )
            return

        # Strip backticks if present
        schema_to_parse = schema_value.strip()
        if schema_to_parse.startswith("`") and schema_to_parse.endswith("`"):
            schema_to_parse = schema_to_parse[1:-1]

        # Check again after stripping backticks
        if not schema_to_parse or schema_to_parse.strip() in ["", "...", "{}", "[]"]:
            self.error_messages.append(
                f"Node {node_id} has an empty or placeholder {schema_type}. Must contain valid field definitions."
            )
            return

        # Try to parse the schema as JSON
        try:
            parsed_schema = json.loads(schema_to_parse)

            # Check if it's an array (form_schema should be)
            if isinstance(parsed_schema, list):
                if len(parsed_schema) == 0:
                    self.error_messages.append(
                        f"Node {node_id} {schema_type} is an empty array. Must contain at least one field definition."
                    )
                else:
                    # Validate each field in the schema
                    required_properties = [
                        "type",
                        "name",
                        "label",
                        "defaultValue",
                        "dataType",
                        "required",
                        "readonly",
                    ]

                    for idx, field in enumerate(parsed_schema):
                        if not isinstance(field, dict):
                            self.error_messages.append(
                                f"Node {node_id} {schema_type} field {idx} is not an object."
                            )
                            continue

                        # Check for all required properties
                        missing_props = [
                            prop for prop in required_properties if prop not in field
                        ]
                        if missing_props:
                            self.error_messages.append(
                                f"Node {node_id} {schema_type} field '{field.get('name', idx)}' is missing required properties: {', '.join(missing_props)}"
                            )

                        # Check that type is "input" only
                        if "type" in field and field["type"] not in ["input"]:
                            self.error_messages.append(
                                f"Node {node_id} {schema_type} field '{field.get('name', idx)}' has invalid type '{field['type']}'. Only 'input' type is supported."
                            )

                        # Check for format field if dataType is string
                        if field.get("dataType") == "string" and "format" not in field:
                            self.error_messages.append(
                                f"Node {node_id} {schema_type} field '{field.get('name', idx)}' with dataType 'string' is missing 'format' property."
                            )
            elif isinstance(parsed_schema, dict):
                # For data_json_schema in login_form links
                if (
                    schema_type == "data_json_schema"
                    or "data_json_schema" in schema_type
                ):
                    if (
                        "properties" not in parsed_schema
                        and "type" not in parsed_schema
                    ):
                        self.error_messages.append(
                            f"Node {node_id} {schema_type} appears to be a JSON schema but is missing 'properties' or 'type' field."
                        )
        except json.JSONDecodeError as e:
            self.error_messages.append(
                f"Node {node_id} {schema_type} contains invalid JSON: {str(e)}"
            )
        except Exception as e:
            self.error_messages.append(
                f"Node {node_id} {schema_type} validation error: {str(e)}"
            )

    def validate_condition_data_types(self) -> None:
        """Validate that condition nodes use valid data_type values and structure."""
        valid_condition_types = self.constants["valid_condition_types"]
        valid_condition_data_types = self.constants["valid_condition_data_types"]

        for node_id, node in self.workflow["nodes"].items():
            if node.get("type") == "condition" and "condition" in node:
                condition = node["condition"]

                # Check condition type
                if "type" in condition:
                    cond_type = condition["type"]
                    if cond_type not in valid_condition_types:
                        if cond_type == "expression":
                            self.error_messages.append(
                                f"Node {node_id} has invalid condition type: 'expression'. "
                                f"Condition nodes must use 'type': 'generic'. "
                                f"Put the expression in the 'field' property instead."
                            )
                        else:
                            self.error_messages.append(
                                f"Node {node_id} has invalid condition type: '{cond_type}'. "
                                f"Valid types are: {', '.join(valid_condition_types)}"
                            )
                else:
                    self.error_messages.append(
                        f"Node {node_id} condition is missing 'type' field. Must be 'generic'."
                    )

                # Check data_type
                if "data_type" in condition:
                    data_type = condition["data_type"]
                    if data_type not in valid_condition_data_types:
                        self.error_messages.append(
                            f"Node {node_id} has invalid condition data_type: '{data_type}'. "
                            f"Valid types are: {', '.join(valid_condition_data_types)}"
                        )
                else:
                    self.error_messages.append(
                        f"Node {node_id} condition is missing required 'data_type' field. "
                        f"Must be one of: {', '.join(valid_condition_data_types)}"
                    )

                # Check that field and value expressions exist
                if "field" not in condition:
                    self.error_messages.append(
                        f"Node {node_id} condition is missing required 'field' field."
                    )

                if "value" not in condition:
                    self.error_messages.append(
                        f"Node {node_id} condition is missing required 'value' field."
                    )

    def validate_json_data_format(self) -> None:
        """Validate that json_data and sdk_data nodes use simple JSON format."""
        for node_id, node in self.workflow["nodes"].items():
            if node.get("type") == "action" and "action" in node:
                action = node["action"]
                action_type = action.get("type")

                # Check json_data and sdk_data nodes
                if action_type in ["json_data", "sdk_data"]:
                    if "data" in action:
                        data_field = action["data"]

                        # Check if it's an expression
                        if (
                            isinstance(data_field, dict)
                            and data_field.get("type") == "expression"
                        ):
                            value = data_field.get("value", "")

                            # Check for template string pattern
                            if isinstance(value, str):
                                # Pattern 1: Backticks wrapping JSON
                                if value.startswith("`{") and value.endswith("}`"):
                                    if "${" in value:
                                        self.error_messages.append(
                                            f"Node {node_id} ({action_type}) uses template string syntax in 'data' field. "
                                            f"{action_type} nodes should use simple JSON format with direct variable references.\n"
                                            f'  ❌ INCORRECT: `{{"key": "${{variable}}"}}`\n'
                                            f'  ✅ CORRECT: {{"key":variable}}\n'
                                            f"\n"
                                            f"Remove the backticks and ${{}} interpolation. Use direct variable names in the JSON structure."
                                        )
                                # Pattern 2: String value with ${} but no outer backticks
                                elif "${" in value and not value.startswith("`"):
                                    if value.strip().startswith(
                                        "{"
                                    ) and value.strip().endswith("}"):
                                        self.error_messages.append(
                                            f"Node {node_id} ({action_type}) uses ${{}} interpolation in 'data' field. "
                                            f"{action_type} nodes should use simple JSON format with direct variable references.\n"
                                            f'  ❌ INCORRECT: {{"key": "${{variable}}"}}\n'
                                            f'  ✅ CORRECT: {{"key":variable}}\n'
                                            f"\n"
                                            f"Use direct variable names in the JSON structure without ${{}} syntax."
                                        )


if __name__ == "__main__":
    JourneyRequiredFieldsValidator.main()
