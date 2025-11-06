# Email OTP Password Reset Journey

## User Request

Create a journey that allows a user to reset their password with an email OTP. Then suggest registering a passkey and register the passkey if the user accepts.

## Journey Generation Instructions

### Email OTP Password Reset with Passkey Suggestion Journey

Build a journey that enables users to securely reset their passwords using email-based One-Time Password (OTP) verification, followed by an optional passkey registration suggestion. This journey is designed for users who have forgotten their passwords and need to regain access to their accounts.

#### Step 1: Email Collection
Present the user with a form to collect their email address. This form should be straightforward and focused solely on gathering the email associated with their account.

#### Step 2: User Existence Verification  
🔴 **CRITICAL PATTERN**: Use `get_user_identifiers` with `user_id_type: "email"` to check if the provided email belongs to any existing user. Unlike authentication flows, this uses the email directly as the lookup key.

- **success_child path**: User exists for this email → proceed to OTP sending
- **failure path**: No user found for this email → reject the journey

#### Step 3: Email OTP Authentication
Use the email OTP authentication node which handles both sending the OTP code to the verified email address and validating the user's input. This single step manages the entire OTP verification process.

#### Step 4: New Password Collection
Present a secure form for the user to enter their new password. Include appropriate password strength requirements and confirmation fields.

#### Step 5: Password Registration
Register the new password for the user using the password registration functionality.

#### Step 6: Passkey Suggestion
After successful password reset, display an informational message suggesting the benefits of passkey registration for enhanced security and convenience.

#### Step 7: Passkey Choice
Present the user with a choice form asking if they would like to register a passkey now or skip this step.

#### Step 8: Conditional Passkey Registration
Based on the user's choice:
- **If they choose to register**: Proceed with WebAuthn passkey registration
- **If they choose to skip**: Complete the journey successfully

#### Step 9: Passkey Registration (Optional Path)
If the user opts for passkey registration, configure WebAuthn registration with appropriate settings for discoverable credentials.

#### Step 10: Journey Completion
Complete the journey with appropriate success messaging, whether the user registered a passkey or not.

### Flow Sequence
1. Email Form → Check User Exists (by email) → Email OTP Authentication
2. New Password Form → Register Password  
3. Passkey Suggestion → User Choice → Conditional Passkey Registration
4. Journey Completion

### Notable Features
- **Secure Verification**: Email OTP ensures only the rightful account owner can reset the password
- **Enhanced Security Option**: Optional passkey registration for future passwordless authentication
- **User Choice**: Non-mandatory passkey registration respects user preferences
- **Clear Messaging**: Informative steps guide users through the process

## Complete Journey JSON

```json
{
  "exports": [
    {
      "path": "tsasm:///applications/default_application/policies/email_otp_password_reset_with_passkey_suggestion",
      "data": {
        "policy_id": "email_otp_password_reset_with_passkey_suggestion",
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
              "id": "a1b2c3d4-e5f6-7890-1234-567890abcdef",
              "head": "f1a2b3c4-d5e6-7890-1234-567890abcdef",
              "nodes": {
                "f1a2b3c4-d5e6-7890-1234-567890abcdef": {
                  "id": "f1a2b3c4-d5e6-7890-1234-567890abcdef",
                  "type": "action",
                  "strings": [],
                  "output_var": "emailData",
                  "action": {
                    "type": "form",
                    "metadata": {
                      "type": "get_information"
                    },
                    "form_id": "password_reset_email_form",
                    "app_data": {
                      "type": "expression",
                      "value": "{}"
                    },
                    "form_schema": {
                      "type": "expression",
                      "value": "[\n  {\n    \"type\": \"input\",\n    \"name\": \"email\",\n    \"label\":\"\",\n    \"defaultValue\":\"\",\n    \"dataType\": \"string\",\n    \"format\": \"email\",\n    \"required\": true,\n    \"readonly\": false\n  }\n]"
                    },
                    "var_name": "emailData"
                  },
                  "links": [
                    {
                      "name": "child",
                      "type": "branch",
                      "target": "a2b3c4d5-e6f7-8901-2345-678901abcdef"
                    }
                  ]
                },
                "a2b3c4d5-e6f7-8901-2345-678901abcdef": {
                  "id": "a2b3c4d5-e6f7-8901-2345-678901abcdef",
                  "type": "transmit_platform_get_user_identifiers",
                  "user_identifier": {
                    "type": "expression",
                    "value": "emailData.email"
                  },
                  "user_id_type": "email",
                  "output_var": "userIdentifiers",
                  "links": [
                    {
                      "name": "success_child",
                      "type": "branch",
                      "target": "b3c4d5e6-f7a8-9012-3456-789012abcdef"
                    },
                    {
                      "name": "failure",
                      "type": "escape",
                      "target": "c4d5e6f7-a8b9-0123-4567-890123abcdef"
                    }
                  ],
                  "error_variable": "error",
                  "metadata": {}
                },
                "b3c4d5e6-f7a8-9012-3456-789012abcdef": {
                  "id": "b3c4d5e6-f7a8-9012-3456-789012abcdef",
                  "type": "transmit_platform_email_otp_authentication",
                  "user_identifier": {
                    "type": "expression",
                    "value": "emailData.email"
                  },
                  "email": {
                    "type": "expression",
                    "value": "emailData.email"
                  },
                  "links": [
                    {
                      "name": "success_child",
                      "type": "branch",
                      "target": "e6f7a8b9-c0d1-2345-6789-012345abcdef"
                    },
                    {
                      "name": "failure",
                      "type": "escape",
                      "target": "c4d5e6f7-a8b9-0123-4567-890123abcdef"
                    }
                  ],
                  "metadata": {},
                  "error_variable": "error"
                },
                "e6f7a8b9-c0d1-2345-6789-012345abcdef": {
                  "id": "e6f7a8b9-c0d1-2345-6789-012345abcdef",
                  "type": "action",
                  "strings": [],
                  "output_var": "passwordData",
                  "action": {
                    "type": "form",
                    "metadata": {
                      "type": "get_information"
                    },
                    "form_id": "reset_password_form",
                    "app_data": {
                      "type": "expression",
                      "value": "{}"
                    },
                    "form_schema": {
                      "type": "expression",
                      "value": "[\n  {\n    \"type\": \"input\",\n    \"name\": \"password\",\n    \"label\":\"\",\n    \"defaultValue\":\"\",\n    \"dataType\": \"string\",\n    \"format\": \"password\",\n    \"required\": true,\n    \"readonly\": false\n  }\n]"
                    },
                    "var_name": "passwordData"
                  },
                  "links": [
                    {
                      "name": "child",
                      "type": "branch",
                      "target": "f7a8b9c0-d1e2-3456-7890-123456abcdef"
                    }
                  ]
                },
                "f7a8b9c0-d1e2-3456-7890-123456abcdef": {
                  "id": "f7a8b9c0-d1e2-3456-7890-123456abcdef",
                  "type": "transmit_platform_password_registration",
                  "user_identifier": {
                    "type": "expression",
                    "value": "emailData.email"
                  },
                  "password": {
                    "type": "expression",
                    "value": "passwordData.password"
                  },
                  "links": [
                    {
                      "name": "success_child",
                      "type": "branch",
                      "target": "a8b9c0d1-e2f3-4567-8901-234567abcdef"
                    },
                    {
                      "name": "failure",
                      "type": "escape",
                      "target": "c4d5e6f7-a8b9-0123-4567-890123abcdef"
                    }
                  ],
                  "metadata": {},
                  "error_variable": "error"
                },
                "a8b9c0d1-e2f3-4567-8901-234567abcdef": {
                  "id": "a8b9c0d1-e2f3-4567-8901-234567abcdef",
                  "type": "action",
                  "strings": [],
                  "action": {
                    "type": "information",
                    "title": {
                      "type": "expression",
                      "value": "\"Password Reset Successful\""
                    },
                    "text": {
                      "type": "expression",
                      "value": "\"Your password has been successfully reset. You can now log in with your new password.\""
                    },
                    "button_text": {
                      "type": "expression",
                      "value": "\"Continue\""
                    },
                    "metadata": {
                      "type": "information"
                    }
                  },
                  "links": [
                    {
                      "name": "child",
                      "type": "branch",
                      "target": "b9c0d1e2-f3a4-5678-9012-345678abcdef"
                    }
                  ]
                },
                "b9c0d1e2-f3a4-5678-9012-345678abcdef": {
                  "id": "b9c0d1e2-f3a4-5678-9012-345678abcdef",
                  "type": "action",
                  "strings": [],
                  "action": {
                    "type": "information",
                    "title": {
                      "type": "expression",
                      "value": "\"Enhanced Security Available\""
                    },
                    "text": {
                      "type": "expression",
                      "value": "\"For enhanced security and convenience, we recommend setting up a passkey. Passkeys provide passwordless authentication using your device's biometrics or PIN.\""
                    },
                    "button_text": {
                      "type": "expression",
                      "value": "\"Continue\""
                    },
                    "metadata": {
                      "type": "information"
                    }
                  },
                  "links": [
                    {
                      "name": "child",
                      "type": "branch",
                      "target": "c0d1e2f3-a4b5-6789-0123-456789abcdef"
                    }
                  ]
                },
                "c0d1e2f3-a4b5-6789-0123-456789abcdef": {
                  "id": "c0d1e2f3-a4b5-6789-0123-456789abcdef",
                  "type": "action",
                  "strings": [],
                  "output_var": "choiceData",
                  "action": {
                    "type": "form",
                    "metadata": {
                      "type": "get_information"
                    },
                    "form_id": "passkey_choice_form",
                    "app_data": {
                      "type": "expression",
                      "value": "{}"
                    },
                    "form_schema": {
                      "type": "expression",
                      "value": "[\n  {\n    \"type\": \"input\",\n    \"name\": \"choice\",\n    \"label\": \"Would you like to register a passkey? (yes/no)\",\n    \"defaultValue\":\"\",\n    \"dataType\": \"string\",\n    \"format\": \"text\",\n    \"required\": true,\n    \"readonly\": false\n  }\n]"
                    },
                    "var_name": "choiceData"
                  },
                  "links": [
                    {
                      "name": "child",
                      "type": "branch",
                      "target": "d1e2f3a4-b5c6-7890-1234-567890abcdef"
                    }
                  ]
                },
                "d1e2f3a4-b5c6-7890-1234-567890abcdef": {
                  "id": "d1e2f3a4-b5c6-7890-1234-567890abcdef",
                  "type": "condition",
                  "condition": {
                    "negated": false,
                    "type": "generic",
                    "metadata": {
                      "type": "condition"
                    },
                    "field": {
                      "type": "expression",
                      "value": "`choiceData.choice`"
                    },
                    "operation": "==",
                    "value": {
                      "type": "expression",
                      "value": "\"yes\""
                    },
                    "data_type": "string"
                  },
                  "links": [
                    {
                      "name": "true",
                      "type": "branch",
                      "target": "e2f3a4b5-c6d7-8901-2345-678901abcdef"
                    },
                    {
                      "name": "false",
                      "type": "branch",
                      "target": "f3a4b5c6-d7e8-9012-3456-789012abcdef"
                    }
                  ]
                },
                "e2f3a4b5-c6d7-8901-2345-678901abcdef": {
                  "id": "e2f3a4b5-c6d7-8901-2345-678901abcdef",
                  "type": "transmit_platform_web_authn_registration",
                  "user_identifier": {
                    "type": "expression",
                    "value": "emailData.email"
                  },
                  "display_name": {
                    "type": "expression",
                    "value": "emailData.email"
                  },
                  "allow_cross_platform_authenticators": true,
                  "register_as_discoverable": true,
                  "links": [
                    {
                      "name": "success_child",
                      "type": "branch",
                      "target": "a4b5c6d7-e8f9-0123-4567-890123abcdef"
                    },
                    {
                      "name": "failure",
                      "type": "branch",
                      "target": "b5c6d7e8-f9a0-1234-5678-901234abcdef"
                    }
                  ],
                  "metadata": {}
                },
                "a4b5c6d7-e8f9-0123-4567-890123abcdef": {
                  "id": "a4b5c6d7-e8f9-0123-4567-890123abcdef",
                  "type": "action",
                  "strings": [],
                  "action": {
                    "type": "information",
                    "title": {
                      "type": "expression",
                      "value": "\"Passkey Registered Successfully\""
                    },
                    "text": {
                      "type": "expression",
                      "value": "\"Your passkey has been registered successfully. You can now use passwordless authentication for future logins.\""
                    },
                    "button_text": {
                      "type": "expression",
                      "value": "\"Complete\""
                    },
                    "metadata": {
                      "type": "information"
                    }
                  },
                  "links": [
                    {
                      "name": "child",
                      "type": "branch",
                      "target": "f3a4b5c6-d7e8-9012-3456-789012abcdef"
                    }
                  ]
                },
                "b5c6d7e8-f9a0-1234-5678-901234abcdef": {
                  "id": "b5c6d7e8-f9a0-1234-5678-901234abcdef",
                  "type": "action",
                  "strings": [],
                  "action": {
                    "type": "information",
                    "title": {
                      "type": "expression",
                      "value": "\"Passkey Registration Failed\""
                    },
                    "text": {
                      "type": "expression",
                      "value": "\"Passkey registration was not successful, but your password has been reset. You can try registering a passkey later from your account settings.\""
                    },
                    "button_text": {
                      "type": "expression",
                      "value": "\"Complete\""
                    },
                    "metadata": {
                      "type": "information"
                    }
                  },
                  "links": [
                    {
                      "name": "child",
                      "type": "branch",
                      "target": "f3a4b5c6-d7e8-9012-3456-789012abcdef"
                    }
                  ]
                },
                "f3a4b5c6-d7e8-9012-3456-789012abcdef": {
                  "id": "f3a4b5c6-d7e8-9012-3456-789012abcdef",
                  "type": "action",
                  "strings": [],
                  "action": {
                    "type": "auth_pass",
                    "metadata": {
                      "type": "auth_pass"
                    }
                  },
                  "links": []
                },
                "c4d5e6f7-a8b9-0123-4567-890123abcdef": {
                  "id": "c4d5e6f7-a8b9-0123-4567-890123abcdef",
                  "type": "action",
                  "strings": [],
                  "action": {
                    "type": "reject",
                    "metadata": {
                      "type": "reject"
                    }
                  },
                  "links": []
                }
              }
            },
            "version_id": "default_version",
            "state": "version",
            "desc": "default_version"
          }
        ],
        "name": "Email OTP Password Reset with Passkey Suggestion",
        "last_modified_date": 1703097600000,
        "type": "anonymous",
        "desc": "Secure password reset flow using email OTP verification with optional passkey registration"
      },
      "category": "policy",
      "type": "dependency",
      "constraints": [
        {
          "server_version": "8.2.0",
          "type": "server_version"
        },
        {
          "application_type": "ido",
          "type": "application_type"
        },
        {
          "db_version": 5,
          "type": "db_version"
        }
      ],
      "dependencies": []
    }
  ]
}
```

