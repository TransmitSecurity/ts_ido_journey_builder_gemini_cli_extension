# Email OTP Authentication Journey (Email OTP Authentication Journey with Retry Loop)

## User Request

Create an email OTP authentication journey with a retry loop logic

## Journey Generation Instructions

### Email OTP Authentication Journey

#### Building Instructions

Email OTP authentication with retry loop (up to 5 attempts):

1. **Loop Setup**: Check if user authenticated; if not, loop up to 5 times
2. **Form**: Collect username + email address  
3. **Email Verification**: Get user emails, check if provided email belongs to username
4. **OTP Flow**: If email matches, send OTP and validate; if not, set error
5. **Completion**: Success exits loop; failure retries or ends after max attempts

🔴 **AUTH PATTERN**: Use `user_id_type: "username"` + email verification condition
⚠️ **Reset Pattern**: Use `user_id_type: "email"` with direct links

#### Flow Sequence
1. Loop (up to 5 attempts) → Login Form (Username & Email) → Get User Emails
2. Condition: Email Match?
   - No: Set Error, Retry Loop
   - Yes: Send OTP, Authenticate
3. On Success: Complete Journey
4. On Failure: Error Feedback, Retry Loop

**Features**: Retry logic (5 attempts), error handling, email verification, secure OTP, variable scoping

## Complete Journey JSON

```json
{
  "workflow": {
    "id": "35a4e8e5-8349-4f92-93a0-5ac045c4d5a9",
    "nodes": {
      "a1b2c3d4-e5f6-7890-1234-567890abcdef": {
        "id": "a1b2c3d4-e5f6-7890-1234-567890abcdef",
        "type": "action",
        "action": {
          "type": "set_variables",
          "variables": [
            {
              "name": "loginForm",
              "value": {
                "type": "expression",
                "value": "{\"username\": \"\", \"password\": \"\"}"
              }
            }
          ]
        },
        "links": [
          {
            "name": "child",
            "type": "branch",
            "target": "f34d1ba6-d7c0-47eb-8af9-b13f2009ee8c"
          }
        ]
      },
      "f34d1ba6-d7c0-47eb-8af9-b13f2009ee8c": {
        "id": "f34d1ba6-d7c0-47eb-8af9-b13f2009ee8c",
        "type": "loop",
        "loop_body": {
          "id": "14aeb8db-2cf9-45b9-b0b2-b9f05c21a014",
          "type": "action",
          "links": [
            {
              "name": "email_otp",
              "type": "escape",
              "target": "098460b5-56be-4e05-93c0-68357edd7ba0",
              "presentation": "action",
              "display_name": {
                "type": "expression",
                "value": "`Email OTP`"
              },
              "data_json_schema": {
                "type": "expression",
                "value": "`{\n   \"type\": \"object\",\n  \"properties\": {\n    \"username\": {\n      \"type\": \"string\"\n    },\n    \"email\": {\n      \"type\": \"string\",\n      \"format\": \"email\"\n    }\n  }\n}`"
              }
            }
          ],
          "output_var": "loginForm",
          "strings": [],
          "action": {
            "form_description": "Email OTP authentication",
            "metadata": {
              "type": "login_form"
            },
            "form_id": "login_form_otp",
            "app_data": {
              "type": "expression",
              "value": "{}"
            },
            "type": "form",
            "var_name": "loginForm",
            "error_data": {
              "type": "expression",
              "value": "error"
            }
          }
        },
        "links": [
          {
            "name": "child",
            "type": "branch",
            "target": "e2312bb3-ac1a-46ff-9a40-093f0cd86100"
          }
        ],
        "max_iterations": 5,
        "condition": {
          "type": "expression",
          "value": "! @policy.isUserAuthenticated()"
        },
        "iteration_count": 0,
        "variables": [
          {
            "name": "error",
            "value": {
              "type": "expression",
              "value": "null"
            }
          }
        ],
        "metadata": {}
      },
      "14aeb8db-2cf9-45b9-b0b2-b9f05c21a014": {
        "id": "14aeb8db-2cf9-45b9-b0b2-b9f05c21a014",
        "type": "action",
        "links": [
          {
            "name": "email_otp",
            "type": "escape",
            "target": "098460b5-56be-4e05-93c0-68357edd7ba0",
            "presentation": "action",
            "display_name": {
              "type": "expression",
              "value": "`Email OTP`"
            },
            "data_json_schema": {
              "type": "expression",
              "value": "`{\n   \"type\": \"object\",\n  \"properties\": {\n    \"username\": {\n      \"type\": \"string\"\n    },\n    \"email\": {\n      \"type\": \"string\",\n      \"format\": \"email\"\n    }\n  }\n}`"
            }
          }
        ],
        "output_var": "loginForm",
        "strings": [],
        "action": {
          "form_description": "Email OTP authentication",
          "metadata": {
            "type": "login_form"
          },
          "form_id": "login_form_retry",
          "app_data": {
            "type": "expression",
            "value": "{}"
          },
          "type": "form",
          "var_name": "loginForm",
          "error_data": {
            "type": "expression",
            "value": "error"
          }
        }
      },
      "098460b5-56be-4e05-93c0-68357edd7ba0": {
        "id": "098460b5-56be-4e05-93c0-68357edd7ba0",
        "type": "transmit_platform_get_user_emails",
        "links": [
          {
            "name": "success_child",
            "type": "branch",
            "target": "43e12410-6cd4-4334-a1fe-9798f168d569"
          }
        ],
        "user_identifier": {
          "type": "expression",
          "value": "loginForm.username"
        },
        "metadata": {},
        "output_var": "userEmails",
        "error_variable": "error"
      },
      "43e12410-6cd4-4334-a1fe-9798f168d569": {
        "id": "43e12410-6cd4-4334-a1fe-9798f168d569",
        "type": "condition",
        "links": [
          {
            "name": "false",
            "type": "branch",
            "target": "9264aa92-b7b9-412d-9b92-e6f9b8c20d0f"
          },
          {
            "name": "true",
            "type": "branch",
            "target": "50030507-ef8a-4995-b3a9-ff0c6164d015"
          }
        ],
        "condition": {
          "negated": false,
          "metadata": {
            "type": "condition"
          },
          "field": {
            "type": "expression",
            "value": "@std.contains(userEmails.list, loginForm.email)"
          },
          "data_type": "boolean",
          "type": "generic",
          "operation": "==",
          "value": {
            "type": "expression",
            "value": "true"
          }
        }
      },
      "9264aa92-b7b9-412d-9b92-e6f9b8c20d0f": {
        "id": "9264aa92-b7b9-412d-9b92-e6f9b8c20d0f",
        "type": "action",
        "links": [],
        "strings": [],
        "action": {
          "variables": [
            {
              "name": "error",
              "value": {
                "type": "expression",
                "value": "`Error sending an email to ${loginForm.email}`"
              }
            }
          ],
          "metadata": {
            "type": "set_variables"
          },
          "type": "set_variables"
        }
      },
      "50030507-ef8a-4995-b3a9-ff0c6164d015": {
        "id": "50030507-ef8a-4995-b3a9-ff0c6164d015",
        "type": "transmit_platform_email_otp_authentication",
        "links": [
          {
            "name": "failure",
            "type": "escape",
            "presentation": "Failure"
          }
        ],
        "user_identifier": {
          "type": "expression",
          "value": "loginForm.username"
        },
        "metadata": {},
        "email": {
          "type": "expression",
          "value": "loginForm.email"
        },
        "error_variable": "error"
      },
      "e2312bb3-ac1a-46ff-9a40-093f0cd86100": {
        "id": "e2312bb3-ac1a-46ff-9a40-093f0cd86100",
        "type": "action",
        "links": [],
        "strings": [],
        "action": {
          "metadata": {
            "type": "auth_pass"
          },
          "type": "auth_pass"
        }
      }
    },
    "head": "a1b2c3d4-e5f6-7890-1234-567890abcdef"
  }
}
```

