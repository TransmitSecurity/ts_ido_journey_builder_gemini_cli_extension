# Simple Loop Example

## User Request

Create a journey that allows the user to try to authenticate via password up to five times before aborting. If the authentication is successful, then collect the user's phone and let it be deregistered, but the journey fails if it fails to be deregistered.

## Journey Generation Instructions

### Password Authentication with Loop and Phone Deregistration

Password authentication with retry loop (up to 5 attempts):

1. **Set Variables**: Set a `clientData` variable with an empty `phone` field
2. **Loop Setup**: Check if user authenticated; if not, loop up to 5 times
  2a. **Login Form**: Give the option for the user to authenticate via password
  2b. **Password Authentication**: Authenticate the user via password. In case of success, the loop will return to the outer scope. 
3. **Collect information**: Get the phone number that the user wishes to deregister
4. **Deregister phone**: Perform the phone dergistration.
5. **Completion**: Success in case of successful deregistration, rejection in case of failure.

### Flow Sequence

**CRITICAL LOOP PATTERN**: IDO loop nodes are conditional branch containers. Nodes inside the loop_body NEVER link back to the loop node or to the first node. Instead, they end with links that have **empty targets** (no "target" field), which automatically causes the loop to retry.

- **Outer Scope** (normal sequential flow):  
  `c462c34d-f67f-46c4-ac34-0f67f306c462` (set variables) → `1f584890-84cd-4b1f-8489-084cd70b1f58` (loop node) → `9636a2ed-bd41-4696-aa2e-0bd410069636` (get information) → `da742dd2-b798-48da-82dd-1b7983c8da74` (deregistration) → success/reject
  
  The outer scope enters the loop, waits for it to complete (up to 5 retries or until condition is false), then continues with data collection and deregistration.

- **Loop Inner Scope** (branch that gets re-executed):  
  Loop's `loop_body` points to → `adf42f1e-1cc0-4bad-82f1-91cc048badf4` (login_form) → `3bfa1f9f-e2cd-413b-a1f9-7e2cdfc13bfa` (password authentication) → **links with NO targets**
  
  **Key mechanism**: The password authentication node (`3bfa1f9f-e2cd-413b-a1f9-7e2cdfc13bfa`) has links like `{"type": "branch"}` and `{"type": "escape"}` with **no "target" field**. This is NOT a dead end - empty targets signal the system to:
  - Re-evaluate the loop condition (`!@policy.isUserAuthenticated`)
  - If true and retries remain: re-execute the loop_body (try authentication again)
  - If false (user authenticated): exit to the loop node's child link
  - If max iterations reached: exit to the loop node's child link
  
  **Never create**: Links from inside the loop back to the loop node (`1f584890-84cd-4b1f-8489-084cd70b1f58`) or to the first node (`adf42f1e-1cc0-4bad-82f1-91cc048badf4`). This causes structural infinite recursion.

## Complete Journey JSON

```json
{
    "exports": [
        {
            "path": "tsasm:///applications/default_application/policies/3b211447-1a7f-44c6-890e-73bd103b0708",
            "data": {
                "policy_id": "3b211447-1a7f-44c6-890e-73bd103b0708",
                "versions": [
                    {
                        "schema_version": 2,
                        "filter_criteria": {
                            "type": "expression",
                            "value": {
                                "type": "expression",
                                "value": "true"
                            }
                        },
                        "workflow": {
                            "head": "c462c34d-f67f-46c4-ac34-0f67f306c462",
                            "nodes": {
                                "c462c34d-f67f-46c4-ac34-0f67f306c462": {
                                    "strings": [],
                                    "action": {
                                        "variables": [
                                            {
                                                "name": "clientData",
                                                "value": {
                                                    "type": "expression",
                                                    "value": "{\"phone\": \"\"}"
                                                }
                                            }
                                        ],
                                        "metadata": {
                                            "type": "set_variables"
                                        },
                                        "type": "set_variables"
                                    },
                                    "links": [
                                        {
                                            "name": "child",
                                            "type": "branch",
                                            "target": "1f584890-84cd-4b1f-8489-084cd70b1f58"
                                        }
                                    ],
                                    "id": "c462c34d-f67f-46c4-ac34-0f67f306c462",
                                    "type": "action"
                                },
                                "da742dd2-b798-48da-82dd-1b7983c8da74": {
                                    "metadata": {},
                                    "phone": {
                                        "type": "expression",
                                        "value": "`clientData.phone`"
                                    },
                                    "links": [
                                        {
                                            "name": "success_child",
                                            "type": "branch",
                                            "target": "1f628a9a-6371-401f-a8a9-36371b701f62"
                                        },
                                        {
                                            "presentation": "Failure",
                                            "name": "failure",
                                            "display_name": {
                                                "type": "expression",
                                                "value": "`Failure`"
                                            },
                                            "type": "escape",
                                            "target": "76019ae8-2f21-4c76-99ae-52f21b7c7601"
                                        }
                                    ],
                                    "id": "da742dd2-b798-48da-82dd-1b7983c8da74",
                                    "type": "transmit_platform_phone_deregistration",
                                    "error_variable": "error"
                                },
                                "3bfa1f9f-e2cd-413b-a1f9-7e2cdfc13bfa": {
                                    "user_identifier": {
                                        "type": "expression",
                                        "value": "loginData1.username"
                                    },
                                    "metadata": {},
                                    "password": {
                                        "type": "expression",
                                        "value": "loginData1.password"
                                    },
                                    "links": [
                                        {
                                            "name": "success_child",
                                            "type": "branch"
                                        },
                                        {
                                            "presentation": "Failure",
                                            "name": "failure",
                                            "display_name": {
                                                "type": "expression",
                                                "value": "`Failure`"
                                            },
                                            "type": "escape"
                                        }
                                    ],
                                    "id": "3bfa1f9f-e2cd-413b-a1f9-7e2cdfc13bfa",
                                    "type": "transmit_platform_password_authentication",
                                    "error_variable": "error",
                                    "organizationMode": "Default"
                                },
                                "1f584890-84cd-4b1f-8489-084cd70b1f58": {
                                    "max_iterations": 5,
                                    "loop_body": {
                                        "strings": [],
                                        "action": {
                                            "metadata": {
                                                "type": "login_form"
                                            },
                                            "form_id": "login_form_1",
                                            "app_data": {
                                                "type": "expression",
                                                "value": "{}"
                                            },
                                            "type": "login_form",
                                            "var_name": "loginData1",
                                            "organizationMode": "Default"
                                        },
                                        "links": [
                                            {
                                                "presentation": "Action",
                                                "name": "password",
                                                "display_name": {
                                                    "type": "expression",
                                                    "value": "`Password`"
                                                },
                                                "type": "escape",
                                                "data_json_schema": {
                                                    "type": "expression",
                                                    "value": "[\n            {\n              \"type\": \"input\",\n              \"name\": \"username\",\n              \"label\": `Username`,\n              \"defaultValue\": ``,\n              \"dataType\": \"string\",\n              \"format\": \"text\",\n              \"required\": true,\n              \"readonly\": false\n            },\n            {\n              \"type\": \"input\",\n              \"name\": \"password\",\n              \"label\": `Password`,\n              \"defaultValue\": ``,\n              \"dataType\": \"string\",\n              \"format\": \"password\",\n              \"required\": true,\n              \"readonly\": false\n            }\n          ]"
                                                },
                                                "target": "3bfa1f9f-e2cd-413b-a1f9-7e2cdfc13bfa"
                                            }
                                        ],
                                        "id": "adf42f1e-1cc0-4bad-82f1-91cc048badf4",
                                        "type": "action",
                                        "output_var": "loginData1"
                                    },
                                    "condition": {
                                        "type": "expression",
                                        "value": "!@policy.isUserAuthenticated"
                                    },
                                    "iteration_count": 0,
                                    "variables": [],
                                    "metadata": {},
                                    "links": [
                                        {
                                            "name": "child",
                                            "type": "branch",
                                            "target": "9636a2ed-bd41-4696-aa2e-0bd410069636"
                                        }
                                    ],
                                    "id": "1f584890-84cd-4b1f-8489-084cd70b1f58",
                                    "type": "loop"
                                },
                                "76019ae8-2f21-4c76-99ae-52f21b7c7601": {
                                    "strings": [],
                                    "action": {
                                        "clear_session": false,
                                        "metadata": {
                                            "type": "reject"
                                        },
                                        "type": "reject"
                                    },
                                    "links": [],
                                    "id": "76019ae8-2f21-4c76-99ae-52f21b7c7601",
                                    "type": "action"
                                },
                                "1f628a9a-6371-401f-a8a9-36371b701f62": {
                                    "strings": [],
                                    "action": {
                                        "metadata": {
                                            "type": "auth_pass"
                                        },
                                        "type": "auth_pass"
                                    },
                                    "links": [],
                                    "id": "1f628a9a-6371-401f-a8a9-36371b701f62",
                                    "type": "action"
                                },
                                "adf42f1e-1cc0-4bad-82f1-91cc048badf4": {
                                    "strings": [],
                                    "action": {
                                        "metadata": {
                                            "type": "login_form"
                                        },
                                        "form_id": "login_form_1",
                                        "app_data": {
                                            "type": "expression",
                                            "value": "{}"
                                        },
                                        "type": "login_form",
                                        "var_name": "loginData1",
                                        "organizationMode": "Default"
                                    },
                                    "links": [
                                        {
                                            "presentation": "Action",
                                            "name": "password",
                                            "display_name": {
                                                "type": "expression",
                                                "value": "`Password`"
                                            },
                                            "type": "escape",
                                            "data_json_schema": {
                                                "type": "expression",
                                                "value": "[\n            {\n              \"type\": \"input\",\n              \"name\": \"username\",\n              \"label\": `Username`,\n              \"defaultValue\": ``,\n              \"dataType\": \"string\",\n              \"format\": \"text\",\n              \"required\": true,\n              \"readonly\": false\n            },\n            {\n              \"type\": \"input\",\n              \"name\": \"password\",\n              \"label\": `Password`,\n              \"defaultValue\": ``,\n              \"dataType\": \"string\",\n              \"format\": \"password\",\n              \"required\": true,\n              \"readonly\": false\n            }\n          ]"
                                            },
                                            "target": "3bfa1f9f-e2cd-413b-a1f9-7e2cdfc13bfa"
                                        }
                                    ],
                                    "id": "adf42f1e-1cc0-4bad-82f1-91cc048badf4",
                                    "type": "action",
                                    "output_var": "loginData1"
                                },
                                "9636a2ed-bd41-4696-aa2e-0bd410069636": {
                                    "strings": [],
                                    "action": {
                                        "metadata": {
                                            "type": "get_information"
                                        },
                                        "form_id": "get_info_from_client_1",
                                        "app_data": {
                                            "type": "expression",
                                            "value": "{}"
                                        },
                                        "type": "form",
                                        "form_schema": {
                                            "type": "expression",
                                            "value": "[\n  {\n    \"type\": \"input\",\n    \"name\": \"userEmail\",\n    \"label\": `Email`,\n    \"defaultValue\": ``,\n    \"dataType\": \"string\",\n    \"format\": \"email\",\n    \"required\": true,\n    \"readonly\": false\n  },\n  {\n    \"type\": \"input\",\n    \"name\": \"userPassword\",\n    \"label\": `Password`,\n    \"defaultValue\": ``,\n    \"dataType\": \"string\",\n    \"format\": \"password\",\n    \"required\": true,\n    \"readonly\": false\n  },\n  {\n    \"type\": \"input\",\n    \"name\": \"phone\",\n    \"label\": ``,\n    \"defaultValue\": ``,\n    \"dataType\": \"string\",\n    \"format\": \"text\",\n    \"required\": true,\n    \"readonly\": false\n  }\n]"
                                        },
                                        "var_name": "clientData"
                                    },
                                    "links": [
                                        {
                                            "name": "child",
                                            "type": "branch",
                                            "target": "da742dd2-b798-48da-82dd-1b7983c8da74"
                                        }
                                    ],
                                    "id": "9636a2ed-bd41-4696-aa2e-0bd410069636",
                                    "type": "action",
                                    "output_var": "clientData"
                                }
                            },
                            "id": "53a6afee-3709-4e53-aafe-c3709ffe53a6"
                        },
                        "version_id": "default_version",
                        "state": "version",
                        "desc": "default_version"
                    }
                ],
                "name": "Simple Loop",
                "last_modified_date": 1761553305297,
                "created_date": 1761552997218,
                "type": "anonymous",
                "config": {
                    "token_create": true,
                    "session_validate": false,
                    "enforce_mosaic_token": null,
                    "session_create": true,
                    "double_encryption": "off",
                    "token_include_request_params": true
                },
                "affinity": "b2c",
                "desc": ""
            },
            "category": "policy",
            "type": "dependency",
            "constraints": [
                {
                    "db_version": 5,
                    "type": "db_version"
                },
                {
                    "application_type": "ido",
                    "type": "application_type"
                }
            ],
            "dependencies": []
        }
    ]
}
```

