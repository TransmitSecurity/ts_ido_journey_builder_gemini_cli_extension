#!/usr/bin/env python3
"""
Journey Metadata Validator

Validates journey-level metadata fields:
- Journey type (must be 'anonymous')
- Required data-level fields: policy_id, type, desc, versions
- Required version-level fields: schema_version, filter_criteria, workflow, version_id, state, desc
- Field type and value validation
- State field validity
"""

from journey_validator_base import JourneyValidatorBase


class JourneyMetadataValidator(JourneyValidatorBase):
    """Validates journey-level metadata."""

    def get_validator_name(self) -> str:
        return "Journey Metadata Validation"

    def run_validations(self) -> None:
        """Run metadata-specific validations."""
        print("✓ Journey type validation")
        self.validate_journey_type()

        print(
            "✓ Required data-level fields validation (policy_id, type, desc, versions)"
        )
        self.validate_data_level_fields()

        print(
            "✓ Required version fields validation (schema_version, filter_criteria, version_id, state, desc)"
        )
        self.validate_required_fields()

    def validate_journey_type(self) -> None:
        """Validate journey metadata fields like type, constraints, etc."""
        # Get valid journey types from constants
        valid_journey_types = self.constants["valid_journey_types"]

        if "exports" in self.journey_data and isinstance(
            self.journey_data["exports"], list
        ):
            if (
                len(self.journey_data["exports"]) > 0
                and "data" in self.journey_data["exports"][0]
            ):
                data = self.journey_data["exports"][0]["data"]

                # Check journey type
                if "type" in data:
                    journey_type = data["type"]
                    if journey_type not in valid_journey_types:
                        self.error_messages.append(
                            f"Invalid journey type: '{journey_type}'. "
                            f"Valid types are: {', '.join(valid_journey_types)}"
                        )
                else:
                    self.error_messages.append(
                        "Journey data is missing required 'type' field. Must be 'anonymous'."
                    )
            else:
                self.error_messages.append(
                    "Journey exports array is empty or missing 'data' field."
                )
        else:
            self.error_messages.append(
                "Journey JSON is missing 'exports' array or it's not a list."
            )

    def validate_data_level_fields(self) -> None:
        """Validate required data-level fields (policy_id, type, desc, versions)."""
        if "exports" in self.journey_data and isinstance(
            self.journey_data["exports"], list
        ):
            if (
                len(self.journey_data["exports"]) > 0
                and "data" in self.journey_data["exports"][0]
            ):
                data = self.journey_data["exports"][0]["data"]

                # Check for required top-level data fields
                required_data_fields = ["policy_id", "type", "desc", "versions"]
                for field in required_data_fields:
                    if field not in data:
                        self.error_messages.append(
                            f"Journey data is missing required field '{field}'"
                        )

                # Validate policy_id field
                if "policy_id" in data:
                    policy_id = data["policy_id"]
                    if not isinstance(policy_id, str):
                        self.error_messages.append(
                            f"Journey data field 'policy_id' must be a string, got {type(policy_id).__name__}"
                        )
                    elif not policy_id.strip():
                        self.error_messages.append(
                            "Journey data field 'policy_id' cannot be empty. Must contain a valid policy ID."
                        )

                # Validate journey-level desc field
                if "desc" in data:
                    desc = data["desc"]
                    if not isinstance(desc, str):
                        self.error_messages.append(
                            f"Journey data field 'desc' must be a string, got {type(desc).__name__}"
                        )
                    # Note: desc can be empty string, so we don't validate length

                # Check versions array
                if "versions" in data and isinstance(data["versions"], list):
                    if len(data["versions"]) == 0:
                        self.error_messages.append(
                            "Journey versions array is empty. Must contain at least one version."
                        )
                elif "versions" in data:
                    self.error_messages.append(
                        "Journey 'versions' field must be a list/array."
                    )

    def validate_required_fields(self) -> None:
        """Validate required version-level fields."""
        if "exports" in self.journey_data and isinstance(
            self.journey_data["exports"], list
        ):
            if (
                len(self.journey_data["exports"]) > 0
                and "data" in self.journey_data["exports"][0]
            ):
                data = self.journey_data["exports"][0]["data"]

                # Check versions array exists and has at least one version
                if "versions" in data and isinstance(data["versions"], list):
                    if len(data["versions"]) > 0:
                        version = data["versions"][0]

                        # Required version fields
                        required_version_fields = [
                            "schema_version",
                            "filter_criteria",
                            "workflow",
                            "version_id",
                            "state",
                            "desc",
                        ]

                        for field in required_version_fields:
                            if field not in version:
                                self.error_messages.append(
                                    f"Journey version is missing required field '{field}'"
                                )

                        # Validate schema_version field
                        if "schema_version" in version:
                            schema_version = version["schema_version"]
                            if not isinstance(schema_version, int):
                                self.error_messages.append(
                                    f"Journey version field 'schema_version' must be an integer, got {type(schema_version).__name__}"
                                )
                            elif schema_version != 2:
                                self.error_messages.append(
                                    f"Journey version field 'schema_version' must be 2, got {schema_version}"
                                )

                        # Validate filter_criteria field
                        if "filter_criteria" in version:
                            filter_criteria = version["filter_criteria"]
                            if not isinstance(filter_criteria, dict):
                                self.error_messages.append(
                                    f"Journey version field 'filter_criteria' must be an object/dict, got {type(filter_criteria).__name__}"
                                )
                            else:
                                # Check that it has required structure
                                if "type" not in filter_criteria:
                                    self.error_messages.append(
                                        "Journey version field 'filter_criteria' must have a 'type' field"
                                    )
                                elif filter_criteria["type"] != "expression":
                                    self.error_messages.append(
                                        f"Journey version field 'filter_criteria' type must be 'expression', got '{filter_criteria['type']}'"
                                    )
                                if "value" not in filter_criteria:
                                    self.error_messages.append(
                                        "Journey version field 'filter_criteria' must have a 'value' field"
                                    )

                        # Validate version_id field
                        if "version_id" in version:
                            version_id = version["version_id"]
                            if not isinstance(version_id, str):
                                self.error_messages.append(
                                    f"Journey version field 'version_id' must be a string, got {type(version_id).__name__}"
                                )
                            elif not version_id.strip():
                                self.error_messages.append(
                                    "Journey version field 'version_id' cannot be empty. Must contain a valid version ID."
                                )

                        # Validate desc field
                        if "desc" in version:
                            desc = version["desc"]
                            if not isinstance(desc, str):
                                self.error_messages.append(
                                    f"Journey version field 'desc' must be a string, got {type(desc).__name__}"
                                )
                            elif not desc.strip():
                                self.error_messages.append(
                                    "Journey version field 'desc' cannot be empty. Must contain a description."
                                )
                            elif len(desc.strip()) < 3:
                                self.error_messages.append(
                                    f"Journey version field 'desc' is too short ('{desc}'). Must contain a meaningful description."
                                )

                        # Validate state field
                        if "state" in version:
                            state = version["state"]
                            valid_states = self.constants["valid_version_states"]
                            if state not in valid_states:
                                self.error_messages.append(
                                    f"Invalid state value '{state}'. "
                                    f"Valid values are: {', '.join(valid_states)}"
                                )


if __name__ == "__main__":
    JourneyMetadataValidator.main()
