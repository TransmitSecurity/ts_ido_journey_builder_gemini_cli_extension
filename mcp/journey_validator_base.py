#!/usr/bin/env python3
"""
Journey Validator Base Class

Provides common functionality for all journey validators:
- CLI argument parsing
- File loading and JSON parsing
- Workflow extraction
- Error message collection and formatting
- Consistent error reporting
- Exit code handling
- Node definitions loading
- Auto-fixing common issues before validation
"""

import json
import os
import sys
from abc import ABC, abstractmethod
from typing import Dict, List, Optional

# Import journey fixes module
try:
    import journey_fixes
except ImportError:
    journey_fixes = None


class JourneyValidatorBase(ABC):
    """Base class for all journey validators."""

    # Class-level variable to store node definitions (loaded once)
    _node_definitions: Optional[Dict] = None

    def __init__(self, auto_fix: bool = True):
        self.error_messages: List[str] = []
        self.journey_data: Optional[Dict] = None
        self.workflow: Optional[Dict] = None
        self.auto_fix: bool = auto_fix

        # Load node definitions if not already loaded
        if JourneyValidatorBase._node_definitions is None:
            JourneyValidatorBase._node_definitions = self._load_node_definitions()

        # Quick access to commonly used data
        self.node_defs = JourneyValidatorBase._node_definitions["nodes"]
        self.constants = JourneyValidatorBase._node_definitions["constants"]

    def _load_node_definitions(self) -> Dict:
        """Load node definitions from node_definitions.json."""
        definitions_path = os.path.join(
            os.path.dirname(__file__), "node_definitions.json"
        )

        try:
            with open(definitions_path, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️  Warning: Could not load node_definitions.json: {e}")
            print("   Validators may not work correctly.")
            return {"nodes": {}, "constants": {}}

    @abstractmethod
    def get_validator_name(self) -> str:
        """Return the name of this validator for display purposes."""
        pass

    @abstractmethod
    def run_validations(self) -> None:
        """
        Run validator-specific validations.
        Subclasses should implement this to perform their specific validation logic.
        Should append errors to self.error_messages.
        Can access self.journey_data and self.workflow.
        """
        pass

    def load_journey_file(self, file_path: str) -> bool:
        """Load journey JSON file. Returns True on success, False on failure."""
        filename = os.path.basename(file_path)
        try:
            with open(file_path, "r") as f:
                self.journey_data = json.load(f)
            print(f"Successfully loaded JSON from {filename}")
            return True
        except Exception as e:
            self.error_messages.append(f"Failed to load Journey JSON file: {e}")
            return False

    def validate_json_structure(self) -> bool:
        """Validate that journey data is a valid dictionary. Returns True if valid."""
        if not isinstance(self.journey_data, dict):
            self.error_messages.append(
                "The journey JSON is not a valid dictionary. Expected a JSON object at the root level."
            )
            return False
        return True

    def extract_workflow(self, required: bool = True) -> bool:
        """
        Extract workflow from journey JSON.

        Args:
            required: If True, adds error if workflow cannot be extracted.
                     If False, silently returns False if workflow not found.

        Returns True if workflow was successfully extracted.
        """
        workflow = None

        if "exports" in self.journey_data:
            if isinstance(self.journey_data["exports"], list):
                if len(self.journey_data["exports"]) > 0:
                    if "data" in self.journey_data["exports"][0]:
                        if "versions" in self.journey_data["exports"][0]["data"]:
                            if (
                                len(self.journey_data["exports"][0]["data"]["versions"])
                                > 0
                            ):
                                if (
                                    "workflow"
                                    in self.journey_data["exports"][0]["data"][
                                        "versions"
                                    ][0]
                                ):
                                    workflow = self.journey_data["exports"][0]["data"][
                                        "versions"
                                    ][0]["workflow"]
                                elif required:
                                    self.error_messages.append(
                                        "The 'versions' key should have included a 'workflow' key."
                                    )
                        elif required:
                            self.error_messages.append(
                                "The 'data' key should have included a 'versions' key."
                            )
                    elif required:
                        self.error_messages.append(
                            "The 'exports' key should have included a 'data' key."
                        )
            elif required:
                self.error_messages.append(
                    "The 'exports' key should have a list value."
                )
        else:
            if "workflow" in self.journey_data:
                workflow = self.journey_data["workflow"]
            elif required:
                self.error_messages.append(
                    "The journey JSON should have an 'exports' or 'workflow' key."
                )

        self.workflow = workflow
        return workflow is not None

    def format_error_report(self) -> Optional[str]:
        """Format error messages into a report. Returns None if no errors."""
        if len(self.error_messages) > 0:
            report = (
                "\n--------------------------------\n"
                f"{self.get_validator_name()} Errors\n"
                "--------------------------------\n"
                + "\n".join(f"🚨 {error}" for error in self.error_messages)
                + "\n--------------------------------"
            )
            return report
        else:
            return None

    def apply_auto_fixes(self, file_path: str) -> bool:
        """Apply auto-fixes using journey_fixes module. Returns True if successful."""
        if not self.auto_fix:
            return True

        if journey_fixes is None:
            print("⚠️  Warning: journey_fixes module not available, skipping auto-fixes")
            return True

        print("\n🔧 Applying auto-fixes...")

        # Suppress the exit call in journey_fixes.main by temporarily replacing sys.exit
        original_exit = sys.exit
        exit_called = [False, 0]

        def mock_exit(code=0):
            exit_called[0] = True
            exit_called[1] = code

        sys.exit = mock_exit

        try:
            # Call the journey_fixes main function
            journey_fixes.main(file_path)

            # If exit was called with error code, return False
            if exit_called[0] and exit_called[1] != 0:
                return False

            return True
        except Exception as e:
            print(f"⚠️  Error during auto-fixes: {e}")
            return False
        finally:
            # Restore original sys.exit
            sys.exit = original_exit

    def validate_file(self, file_path: str) -> int:
        """
        Main validation entry point. Returns exit code (0 for success, 1 for failure).

        This orchestrates the validation process:
        1. Apply auto-fixes (if enabled)
        2. Load file
        3. Validate JSON structure
        4. Extract workflow (if needed)
        5. Run validator-specific validations
        6. Report results
        """
        # Apply auto-fixes before validation
        if not self.apply_auto_fixes(file_path):
            print("❌ Auto-fixes failed, cannot proceed with validation")
            return 1

        # Load file
        if not self.load_journey_file(file_path):
            error_report = self.format_error_report()
            if error_report:
                print(error_report)
            return 1

        # Validate JSON structure
        if not self.validate_json_structure():
            error_report = self.format_error_report()
            if error_report:
                print(error_report)
            return 1

        # Run validator-specific validations
        print(f"\n{self.get_validator_name()}...")
        self.run_validations()

        # Report results
        error_report = self.format_error_report()
        if error_report:
            print(error_report)
            return 1
        else:
            print(f"\n✅ {self.get_validator_name()} passed - no issues found.")
            return 0

    @classmethod
    def main(cls):
        """CLI entry point for the validator."""
        if len(sys.argv) < 2:
            validator = cls()
            print(f"Usage: python {sys.argv[0]} <json_file_path>")
            sys.exit(1)

        file_path = sys.argv[1]
        filename = os.path.basename(file_path)

        if not os.path.isfile(file_path):
            print(f"Error: '{filename}' is not a valid file path.")
            sys.exit(1)

        validator = cls()
        exit_code = validator.validate_file(file_path)
        sys.exit(exit_code)
