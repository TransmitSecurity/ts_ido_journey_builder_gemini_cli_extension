#!/usr/bin/env python3
"""
Journey Expressions Validator

Validates expression syntax and formatting:
- Template literal syntax (backticks, ${} interpolation)
- Valid @std function calls
- Expression escaping (quotes inside backticks)
- Complex template interpolation (prevents parser errors)
- AuthScript-style rules (no single quotes, semicolons, etc.)
- Operator syntax (no ++, --, +=, etc.)
- Loop and condition expression formatting
- Information node expression formatting
"""

import re

from journey_validator_base import JourneyValidatorBase


class JourneyExpressionsValidator(JourneyValidatorBase):
    """Validates expression syntax and formatting."""

    def get_validator_name(self) -> str:
        return "Journey Expressions Validation"

    def run_validations(self) -> None:
        """Run expression-specific validations."""
        # Extract workflow first
        if not self.extract_workflow(required=True):
            return

        print("✓ Expression syntax validation")
        self.validate_expression_syntax()

        print("✓ @std function validation")
        self.validate_std_function_calls()

        print("✓ Expression escaping validation")
        self.validate_expression_escaping()

        print("✓ Complex template interpolation validation")
        self.validate_complex_template_interpolation()

        print("✓ AuthScript-style expression validation")
        self.validate_authscript_style_expressions()

        print("✓ Expression operator syntax validation")
        self.validate_expression_operator_syntax()

        print("✓ Information node expression validation")
        self.validate_information_node_expressions()

    def scan_expressions(self, callback):
        """Scan all expressions in the workflow and apply callback."""
        for node_id, node in self.workflow["nodes"].items():
            # Check if this is an information node
            is_info_node = (
                node.get("type") == "action"
                and node.get("action", {}).get("type") == "information"
            )
            self._scan_dict(node, node_id, "", is_info_node, callback)

    def _scan_dict(self, d, node_id: str, path: str, is_info_node: bool, callback):
        """Recursively scan dictionary for expression values."""
        if isinstance(d, dict):
            # Check if this is an expression object
            if d.get("type") == "expression" and "value" in d:
                callback(d["value"], node_id, path, is_info_node)

            # Recurse into nested structures
            for key, value in d.items():
                new_path = f"{path}.{key}" if path else key
                if isinstance(value, dict):
                    self._scan_dict(value, node_id, new_path, is_info_node, callback)
                elif isinstance(value, list):
                    for idx, item in enumerate(value):
                        if isinstance(item, dict):
                            self._scan_dict(
                                item,
                                node_id,
                                f"{new_path}[{idx}]",
                                is_info_node,
                                callback,
                            )

    def validate_expression_syntax(self) -> None:
        """Validate that expressions have valid syntax."""

        def check_syntax(value: str, node_id: str, field_path: str, is_info_node: bool):
            if not value or not isinstance(value, str):
                return

            # Check for single quotes inside template literals
            if value.startswith("`") and value.endswith("`"):
                interpolation_pattern = r"\$\{([^}]+)\}"
                interpolations = re.findall(interpolation_pattern, value)

                for interpolation in interpolations:
                    if "'" in interpolation:
                        self.error_messages.append(
                            f"Node {node_id} field '{field_path}' contains single quotes (') "
                            f"inside template literal interpolation. IDO expressions do not support "
                            f"single quotes inside template literals. Use double quotes (escaped) instead.\n"
                            f"  ❌ Wrong: `${{error ? 'Failed' : 'Success'}}`\n"
                            f'  ✅ Correct: `${{error ? "Failed" : "Success"}}`'
                        )
                        break

            # Check for invalid @std functions
            std_if_pattern = r"@std\.if\s*\("
            if re.search(std_if_pattern, value):
                self.error_messages.append(
                    f"Node {node_id} field '{field_path}' uses @std.if() which doesn't exist in IDO. "
                    f"Use JavaScript ternary operator instead: condition ? valueIfTrue : valueIfFalse"
                )

            std_default_pattern = r"@std\.default\s*\("
            if re.search(std_default_pattern, value):
                self.error_messages.append(
                    f"Node {node_id} field '{field_path}' uses @std.default() which doesn't exist in IDO. "
                    f"Use JavaScript logical OR or ternary operator instead:\n"
                    f"  ✅ Correct: ${{value || defaultValue}}"
                )

            std_now_pattern = r"@std\.now\s*\("
            if re.search(std_now_pattern, value):
                self.error_messages.append(
                    f"Node {node_id} field '{field_path}' uses @std.now() which doesn't exist in IDO. "
                    f"Use @time.now() instead to get the current timestamp."
                )

        self.scan_expressions(check_syntax)

    def validate_std_function_calls(self) -> None:
        """Validate that all @std function calls use valid function names."""
        valid_std_functions = set(self.constants["valid_std_functions"])

        def check_std_functions(
            value: str, node_id: str, field_path: str, is_info_node: bool
        ):
            if not value or not isinstance(value, str):
                return

            # Pattern to match @std.functionName(
            std_function_pattern = r"@std\.([a-zA-Z_][a-zA-Z0-9_]*)\s*\("
            matches = re.finditer(std_function_pattern, value)

            for match in matches:
                function_name = match.group(1)
                if function_name not in valid_std_functions:
                    # Provide helpful suggestions
                    suggestions = []

                    if function_name in ["is_null", "isNull", "isnull"]:
                        suggestions.append(
                            "  💡 To check for null, use: `variable == null` or `variable != null`"
                        )
                    elif function_name in ["isEmpty", "is_empty", "isempty"]:
                        suggestions.append(
                            "  💡 To check if empty, use: `@std.len(variable) == 0`"
                        )
                    elif function_name in ["concat", "join"]:
                        suggestions.append(
                            "  💡 To concatenate strings, use:\n"
                            "     • Template literals: `${var1} ${var2}`\n"
                            "     • String concatenation: `var1 + var2`"
                        )
                    elif function_name in ["toString", "to_string", "tostring"]:
                        suggestions.append(
                            "  💡 To convert to string, use:\n"
                            "     • Template literals: `${variable}`\n"
                            '     • String concatenation: `variable + ""`'
                        )

                    suggestion_text = (
                        "\n" + "\n".join(suggestions) if suggestions else ""
                    )

                    self.error_messages.append(
                        f"Node {node_id} field '{field_path}' uses invalid @std function: '{function_name}'\n"
                        f"\n"
                        f"  ❌ Invalid: @std.{function_name}(...)\n"
                        f"\n"
                        f"  ✅ Valid @std functions are:\n"
                        f"     {', '.join(sorted(valid_std_functions))}\n"
                        f"{suggestion_text}"
                    )

        self.scan_expressions(check_std_functions)

    def validate_expression_escaping(self) -> None:
        """Validate that expressions don't have incorrectly escaped quotes inside backticks."""

        def check_escaping(
            value: str, node_id: str, field_path: str, is_info_node: bool
        ):
            if not value or not isinstance(value, str):
                return

            # Check if the value contains backticks
            if "`" not in value:
                return

            # Find content inside backticks
            backtick_pattern = r"`([^`]*)`"
            matches = re.finditer(backtick_pattern, value)

            for match in matches:
                content_inside_backticks = match.group(1)

                # Check if there are escaped quotes inside the backticks
                if r"\"" in content_inside_backticks:
                    self.error_messages.append(
                        f"Node {node_id} field '{field_path}' has incorrectly escaped quotes "
                        f'inside backticks. Inside backticks, use " not \\" for quotes. '
                        f"Found: `{content_inside_backticks[:50]}...`"
                    )

        self.scan_expressions(check_escaping)

    def validate_complex_template_interpolation(self) -> None:
        """Validate that template literal interpolations don't contain overly complex expressions."""

        def check_complexity(
            value: str, node_id: str, field_path: str, is_info_node: bool
        ):
            if not value or not isinstance(value, str):
                return

            # Only check template literals (backticks)
            if not (value.startswith("`") and value.endswith("`")):
                return

            # Extract all ${...} interpolations
            interpolation_pattern = r"\$\{([^}]+)\}"
            matches = re.finditer(interpolation_pattern, value)

            for match in matches:
                interpolation_content = match.group(1)

                # Check for complexity indicators:
                # 1. Parentheses with logical operators (||, &&)
                if re.search(r"\([^)]*(\|\||&&)[^)]*\)", interpolation_content):
                    self.error_messages.append(
                        f"Node {node_id} field '{field_path}' has complex expression inside template literal.\n"
                        f"  Problem: ${{{interpolation_content}}}\n"
                        f"\n"
                        f"  Complex expressions with nested parentheses and logical operators can cause parser errors.\n"
                        f"\n"
                        f"  🔧 FIX: Break down the expression using set_variables"
                    )
                    continue

                # 2. Arithmetic operations combined with logical operators
                if re.search(
                    r"(\|\||&&).+[+\-*/]|[+\-*/].+(\|\||&&)", interpolation_content
                ):
                    self.error_messages.append(
                        f"Node {node_id} field '{field_path}' combines logical and arithmetic operators.\n"
                        f"  Problem: ${{{interpolation_content}}}\n"
                        f"\n"
                        f"  🔧 FIX: Use set_variables to break into separate steps."
                    )
                    continue

        self.scan_expressions(check_complexity)

    def validate_authscript_style_expressions(self) -> None:
        """Validate expressions using AuthScript-inspired rules."""
        known_namespaces = self.constants["known_namespaces"]

        def check_authscript_rules(
            value: str, node_id: str, field_path: str, is_info_node: bool
        ):
            if not value or not isinstance(value, str):
                return

            # Rule 1: Check for single quotes in string literals
            cleaned_value = value
            cleaned_value = re.sub(r'"(?:[^"\\]|\\.)*"', "", cleaned_value)
            cleaned_value = re.sub(r"`[^`]*`", "", cleaned_value)

            single_quote_pattern = r"'[^']*'"
            if re.search(single_quote_pattern, cleaned_value):
                self.error_messages.append(
                    f"Node {node_id} field '{field_path}' contains single-quoted strings. "
                    f"IDO expressions should use double quotes for string literals, not single quotes.\n"
                    f"  ❌ WRONG: 'hello world'\n"
                    f'  ✅ CORRECT: "hello world"'
                )

            # Rule 2: Check for semicolons
            if ";" in value:
                value_without_strings = re.sub(r'"(?:[^"\\]|\\.)*"', "", value)
                value_without_strings = re.sub(
                    r"'(?:[^'\\]|\\.)*'", "", value_without_strings
                )

                if ";" in value_without_strings:
                    self.error_messages.append(
                        f"Node {node_id} field '{field_path}' contains semicolons. "
                        f"IDO expressions should be single statements without semicolons."
                    )

            # Rule 3: Check for incorrect @namespace.function syntax
            for namespace in known_namespaces:
                pattern = rf"\b{namespace}\.[a-zA-Z_][a-zA-Z0-9_]*\s*\("
                if re.search(pattern, value):
                    pattern_with_at = rf"@{namespace}\.[a-zA-Z_][a-zA-Z0-9_]*\s*\("
                    if not re.search(pattern_with_at, value):
                        self.error_messages.append(
                            f"Node {node_id} field '{field_path}' has function call using '{namespace}' "
                            f"namespace without @ prefix. Platform function calls must start with @.\n"
                            f"  ❌ WRONG: {namespace}.contains(...)\n"
                            f"  ✅ CORRECT: @{namespace}.contains(...)"
                        )
                        break

            # Rule 4: Check for incorrect operator usage
            if "===" in value or "!==" in value:
                self.error_messages.append(
                    f"Node {node_id} field '{field_path}' uses strict equality operators (=== or !==). "
                    f"IDO expressions use == and != for equality checks.\n"
                    f"  ❌ WRONG: variable === value\n"
                    f"  ✅ CORRECT: variable == value"
                )

        self.scan_expressions(check_authscript_rules)

    def validate_expression_operator_syntax(self) -> None:
        """Validate that expressions use correct operator syntax."""

        def check_operators(
            value: str, node_id: str, field_path: str, is_info_node: bool
        ):
            if not value or not isinstance(value, str):
                return

            # Check for incorrect compound assignment operators
            compound_operators = ["+=", "-=", "*=", "/=", "&=", "|=", "^=", "%="]
            for op in compound_operators:
                if op in value:
                    self.error_messages.append(
                        f"Node {node_id} field '{field_path}' uses compound assignment operator '{op}'. "
                        f"IDO expressions do not support compound assignment operators.\n"
                        f"  ❌ WRONG: variable += 1\n"
                        f"  ✅ CORRECT: variable = variable + 1"
                    )
                    break

            # Check for increment/decrement operators
            if "++" in value or "--" in value:
                self.error_messages.append(
                    f"Node {node_id} field '{field_path}' uses increment/decrement operators (++ or --). "
                    f"IDO expressions do not support ++ or -- operators.\n"
                    f"  ❌ WRONG: counter++\n"
                    f"  ✅ CORRECT: counter = counter + 1"
                )

            # Check for modulo operator
            if "%" in value:
                value_without_strings = re.sub(r'"(?:[^"\\]|\\.)*"', "", value)
                value_without_strings = re.sub(
                    r"'(?:[^'\\]|\\.)*'", "", value_without_strings
                )

                if "%" in value_without_strings:
                    self.error_messages.append(
                        f"Node {node_id} field '{field_path}' uses modulo operator (%). "
                        f"Verify that modulo is supported in your IDO version."
                    )

            # Check for power operator
            if "**" in value:
                self.error_messages.append(
                    f"Node {node_id} field '{field_path}' uses power operator (**). "
                    f"IDO expressions do not support the ** operator for exponentiation."
                )

            # Check for bitwise NOT operator
            if "~" in value:
                value_without_strings = re.sub(r'"(?:[^"\\]|\\.)*"', "", value)
                value_without_strings = re.sub(
                    r"'(?:[^'\\]|\\.)*'", "", value_without_strings
                )

                if "~" in value_without_strings:
                    self.error_messages.append(
                        f"Node {node_id} field '{field_path}' uses bitwise NOT operator (~). "
                        f"IDO expressions do not support the ~ operator."
                    )

        self.scan_expressions(check_operators)

    def validate_information_node_expressions(self) -> None:
        """Validate that information nodes have properly formatted expressions."""

        def check_excessive_backticking(value: str) -> tuple:
            """Check for excessive backticking patterns."""
            if not value or not isinstance(value, str):
                return (False, None)

            # Pattern 1: Double backticks at start/end
            if (
                value.startswith("`` ")
                or value.startswith("``\n")
                or value.endswith(" ``")
                or value.endswith("\n``")
            ):
                if "+" in value and "`" in value[3:-3]:
                    return (
                        True,
                        "Expression has double backticks wrapping concatenated backticked segments. "
                        "Run journey_fixes.py to fix automatically.",
                    )
                else:
                    return (
                        True,
                        "Expression has double backticks at start/end. "
                        "Run journey_fixes.py to fix automatically.",
                    )

            # Pattern 2: Multiple backticked segments concatenated with +
            backticked_concat_pattern = r"`[^`]+`\s*\+\s*[a-zA-Z_][a-zA-Z0-9_.]*"
            if re.search(backticked_concat_pattern, value):
                return (
                    True,
                    "Expression uses inefficient string concatenation with individual backticked segments. "
                    "Run journey_fixes.py to fix automatically.",
                )

            return (False, None)

        for node_id, node in self.workflow["nodes"].items():
            if node.get("type") == "action" and "action" in node:
                action = node["action"]
                if action.get("type") == "information":
                    # Check the text field
                    if "text" in action and isinstance(action["text"], dict):
                        if action["text"].get("type") == "expression":
                            text_value = action["text"].get("value", "")

                            has_excessive, suggestion = check_excessive_backticking(
                                text_value
                            )
                            if has_excessive:
                                self.error_messages.append(
                                    f"Node {node_id} (information) has excessive backticking in text field. "
                                    f"{suggestion}"
                                )

                            # Check for newlines
                            if isinstance(text_value, str) and (
                                "\n" in text_value
                                or "\r" in text_value
                                or "\\n" in text_value
                            ):
                                self.error_messages.append(
                                    f"Node {node_id} (information) has newlines in text expression. "
                                    f"Information node expressions should not contain newlines."
                                )

                    # Check title field
                    if "title" in action and isinstance(action["title"], dict):
                        if action["title"].get("type") == "expression":
                            title_value = action["title"].get("value", "")
                            has_excessive, suggestion = check_excessive_backticking(
                                title_value
                            )
                            if has_excessive:
                                self.error_messages.append(
                                    f"Node {node_id} (information) has excessive backticking in title field. "
                                    f"{suggestion}"
                                )

                    # Check button_text field
                    if "button_text" in action and isinstance(
                        action["button_text"], dict
                    ):
                        if action["button_text"].get("type") == "expression":
                            button_value = action["button_text"].get("value", "")
                            has_excessive, suggestion = check_excessive_backticking(
                                button_value
                            )
                            if has_excessive:
                                self.error_messages.append(
                                    f"Node {node_id} (information) has excessive backticking in button_text field. "
                                    f"{suggestion}"
                                )


if __name__ == "__main__":
    JourneyExpressionsValidator.main()
