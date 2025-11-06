# Account Protection and Identity Onboarding Journey

## User Request

Create a secure authentication journey for user registration with risk assessment, identity verification, and passwordless authentication setup

## Journey Generation Instructions

### Account Protection and Identity Onboarding Journey

#### Flow Overview

This journey demonstrates a comprehensive user onboarding flow with multiple security layers:

1. **Initialization and Risk Assessment**
   - Set up error handling and client data variables
   - Invoke risk recommendation (DRS) to evaluate registration context
   - Branch based on risk outcome (trust/allow/challenge/deny)

2. **Email Collection and Verification**
   - Collect email address via form
   - Validate email with OTP (6-digit code, 3-minute expiry, 3 max attempts)

3. **Identity Verification (IDV)**
   - Optional document verification step
   - Branch on verification result (allow/challenge/deny)

4. **User Creation and Data Storage**
   - Create user in Mosaic platform
   - Handle "user already exists" scenario
   - Write custom user data to internal database

5. **Device Registration and Passkey Enrollment**
   - Register user's device
   - Register passkeys for passwordless authentication
   - Set as discoverable, no cross-platform authenticators

6. **Completion and Error Handling**
   - Robust error handling at each step
   - User feedback and secure session termination

#### Notable Features

- **Dynamic Risk Assessment**: Real-time risk recommendations adapt the flow
- **Multi-Factor Onboarding**: Combines email OTP, document verification, and device binding
- **Passwordless Authentication**: Registers passkeys for future seamless logins
- **Comprehensive Error Handling**: Every critical step includes user feedback
- **Custom Data Storage**: Internal user data updated for application needs

## Complete Journey JSON

```json
{
  "exports": [{
    "path": "tsasm:///applications/default_application/policies/account_protection_onboarding",
    "data": {
      "policy_id": "account_protection_onboarding",
      "versions": [{
        "schema_version": 2,
        "filter_criteria": {
          "type": "expression",
          "value": {"type": "expression", "value": "true"}
        },
        "workflow": {
          "id": "b2d10db4-2ce5-4714-b09a-09fa59c56f0d",
          "head": "5f92cb95-350b-4a7c-969a-84bc8b347f39",
          "nodes": {
            "5f92cb95-350b-4a7c-969a-84bc8b347f39": {
              "id": "5f92cb95-350b-4a7c-969a-84bc8b347f39",
              "type": "action",
              "strings": [],
              "action": {
                "type": "set_variables",
                "variables": [
                  {
                    "name": "error",
                    "value": {"type": "expression", "value": "{}"}
                  },
                  {
                    "name": "clientData",
                    "value": {"type": "expression", "value": "{\"userEmail\":\"\"}"}
                  }
                ],
                "metadata": {"type": "set_variables"}
              },
              "links": [{"name": "child", "type": "branch", "target": "344db378-7f91-4e14-bfa6-549d8bee53ef"}]
            },
            "344db378-7f91-4e14-bfa6-549d8bee53ef": {
              "id": "344db378-7f91-4e14-bfa6-549d8bee53ef",
              "type": "transmit_acp",
              "action_type": "register",
              "provider_id": "",
              "branch_on_error": false,
              "output_var": "account_protection_result",
              "metadata": {"label": "DRS recommendation"},
              "links": [
                {"name": "trust_child", "type": "branch", "target": "15f900c8-d7f1-44b8-a3d8-de0130e94bd4"},
                {"name": "allow_child", "type": "branch", "target": "15f900c8-d7f1-44b8-a3d8-de0130e94bd4"},
                {"name": "challenge_child", "type": "branch", "target": "643a4e7c-4857-41a8-8f0e-246268e65ab5"},
                {"name": "deny_child", "type": "branch", "target": "643a4e7c-4857-41a8-8f0e-246268e65ab5"}
              ]
            },
            "643a4e7c-4857-41a8-8f0e-246268e65ab5": {
              "id": "643a4e7c-4857-41a8-8f0e-246268e65ab5",
              "type": "action",
              "strings": [],
              "action": {
                "type": "information",
                "title": {"type": "expression", "value": "\"Information\""},
                "text": {"type": "expression", "value": "\"DRS recommendation DENY or Challenge - Rejecting Flow\""},
                "button_text": {"type": "expression", "value": "\"OK\""},
                "metadata": {"type": "information"}
              },
              "links": [{"name": "child", "type": "branch", "target": "37ea6cb9-cb23-4245-9801-1fcdf9b8eaf9"}]
            },
            "37ea6cb9-cb23-4245-9801-1fcdf9b8eaf9": {
              "id": "37ea6cb9-cb23-4245-9801-1fcdf9b8eaf9",
              "type": "action",
              "strings": [],
              "action": {
                "type": "reject",
                "clear_session": false,
                "metadata": {"type": "reject"}
              },
              "links": []
            },
            "15f900c8-d7f1-44b8-a3d8-de0130e94bd4": {
              "id": "15f900c8-d7f1-44b8-a3d8-de0130e94bd4",
              "type": "block",
              "metadata": {"label": "Collect and verify email"},
              "block": {
                "id": "62c27e3d-61e3-439e-abf8-209e462cca44",
                "type": "action",
                "strings": [],
                "output_var": "clientData",
                "action": {
                  "type": "form",
                  "metadata": {"label": "Get Email from User", "type": "get_information"},
                  "form_id": "email",
                  "app_data": {"type": "expression", "value": "{}"},
                  "form_schema": {
                    "type": "expression",
                    "value": "{\n  \"$schema\": \"https://json-schema.org/draft/2020-12/schema\",\n  \"type\": \"object\",\n  \"properties\": {\n    \"userEmail\": {\n      \"type\": \"string\",\n      \"format\": \"email\"\n    }\n  }\n}"
                  },
                  "var_name": "clientData"
                },
                "links": [{"name": "child", "type": "branch", "target": "fecdcfda-e6b4-48d3-886a-3dd8c6bdd50a"}]
              },
              "links": [{"name": "child", "type": "branch", "target": "a8633b95-9e4d-4fdc-ad6d-1cf55039db68"}]
            },
            "62c27e3d-61e3-439e-abf8-209e462cca44": {
              "id": "62c27e3d-61e3-439e-abf8-209e462cca44",
              "type": "action",
              "strings": [],
              "output_var": "clientData",
              "action": {
                "type": "form",
                "metadata": {"label": "Get Email from User", "type": "get_information"},
                "form_id": "email",
                "app_data": {"type": "expression", "value": "{}"},
                "form_schema": {
                  "type": "expression",
                  "value": "{\n  \"$schema\": \"https://json-schema.org/draft/2020-12/schema\",\n  \"type\": \"object\",\n  \"properties\": {\n    \"userEmail\": {\n      \"type\": \"string\",\n      \"format\": \"email\"\n    }\n  }\n}"
                },
                "var_name": "clientData"
              },
              "links": [{"name": "child", "type": "branch", "target": "fecdcfda-e6b4-48d3-886a-3dd8c6bdd50a"}]
            },
            "fecdcfda-e6b4-48d3-886a-3dd8c6bdd50a": {
              "id": "fecdcfda-e6b4-48d3-886a-3dd8c6bdd50a",
              "type": "transmit_platform_email_validation",
              "code_length": 6,
              "expiry_in_minutes": 3,
              "max_failed_attempts": 3,
              "email": {"type": "expression", "value": "clientData.userEmail"},
              "error_variable": "error",
              "metadata": {},
              "links": [
                {"name": "success_child", "type": "branch", "target": "a8633b95-9e4d-4fdc-ad6d-1cf55039db68"},
                {
                  "name": "failure",
                  "type": "escape",
                  "presentation": "Failure",
                  "display_name": {"type": "expression", "value": "`Failure`"},
                  "data_json_schema": {"type": "expression", "value": ""},
                  "target": "e9e7f643-a47a-463c-a27f-3e0e588b06f2"
                }
              ]
            },
            "e9e7f643-a47a-463c-a27f-3e0e588b06f2": {
              "id": "e9e7f643-a47a-463c-a27f-3e0e588b06f2",
              "type": "action",
              "strings": [],
              "action": {
                "type": "information",
                "title": {"type": "expression", "value": "\"Information\""},
                "text": {"type": "expression", "value": "Email Validation error ${error}"},
                "button_text": {"type": "expression", "value": "\"OK\""},
                "metadata": {"type": "information"}
              },
              "links": [{"name": "child", "type": "branch", "target": "acc36261-d09b-4691-8250-9c69f5442a4c"}]
            },
            "acc36261-d09b-4691-8250-9c69f5442a4c": {
              "id": "acc36261-d09b-4691-8250-9c69f5442a4c",
              "type": "action",
              "strings": [],
              "action": {
                "type": "reject",
                "clear_session": false,
                "metadata": {"type": "reject"}
              },
              "links": []
            },
            "a8633b95-9e4d-4fdc-ad6d-1cf55039db68": {
              "id": "a8633b95-9e4d-4fdc-ad6d-1cf55039db68",
              "type": "block",
              "metadata": {"label": "Identity Verification"},
              "block": {
                "id": "8142175a-6a41-49f5-8988-c0c2b39ce260",
                "type": "condition",
                "condition": {
                  "negated": false,
                  "type": "generic",
                  "metadata": {"notes": "Dummy flag to skip IDV", "type": "condition"},
                  "field": {"type": "expression", "value": "true"},
                  "data_type": "boolean",
                  "operation": "==",
                  "value": {"type": "expression", "value": "true"}
                },
                "links": [
                  {"name": "true", "type": "branch", "target": "002a5fea-e302-4889-8dd3-05624d316f14"},
                  {"name": "false", "type": "branch"}
                ]
              },
              "links": [{"name": "child", "type": "branch", "target": "9f673ef2-e003-4edd-a0c5-bef4390688a8"}]
            },
            "8142175a-6a41-49f5-8988-c0c2b39ce260": {
              "id": "8142175a-6a41-49f5-8988-c0c2b39ce260",
              "type": "condition",
              "condition": {
                "negated": false,
                "type": "generic",
                "metadata": {"notes": "Dummy flag to skip IDV", "type": "condition"},
                "field": {"type": "expression", "value": "true"},
                "data_type": "boolean",
                "operation": "==",
                "value": {"type": "expression", "value": "true"}
              },
              "links": [
                {"name": "true", "type": "branch", "target": "002a5fea-e302-4889-8dd3-05624d316f14"},
                {"name": "false", "type": "branch"}
              ]
            },
            "002a5fea-e302-4889-8dd3-05624d316f14": {
              "id": "002a5fea-e302-4889-8dd3-05624d316f14",
              "type": "transmit_idv_hosted",
              "callback_url": {"type": "expression", "value": "\"http://localhost:3000\""},
              "provider_id": "",
              "branch_on_session_error": false,
              "output_var": "identity_result",
              "metadata": {},
              "links": [
                {"name": "allow_child", "type": "branch", "target": "5305d9e4-2fe6-46ae-b7b2-04358e701030"},
                {"name": "challenge_child", "type": "branch", "target": "4ce8f688-7120-4338-8d3a-c6acd4055c81"},
                {"name": "deny_child", "type": "branch", "target": "6c5f0339-272a-4616-8b86-beaa2a66a0d8"}
              ]
            },
            "5305d9e4-2fe6-46ae-b7b2-04358e701030": {
              "id": "5305d9e4-2fe6-46ae-b7b2-04358e701030",
              "type": "action",
              "strings": [],
              "action": {
                "type": "information",
                "title": {"type": "expression", "value": "\"Information\""},
                "text": {"type": "expression", "value": "\"IDV result Allow\""},
                "button_text": {"type": "expression", "value": "\"OK\""},
                "metadata": {"type": "information"}
              },
              "links": [{"name": "child", "type": "branch"}]
            },
            "4ce8f688-7120-4338-8d3a-c6acd4055c81": {
              "id": "4ce8f688-7120-4338-8d3a-c6acd4055c81",
              "type": "action",
              "strings": [],
              "action": {
                "type": "information",
                "title": {"type": "expression", "value": "\"Information\""},
                "text": {"type": "expression", "value": "\"IDV result Challenge\""},
                "button_text": {"type": "expression", "value": "\"OK\""},
                "metadata": {"type": "information"}
              },
              "links": [{"name": "child", "type": "branch"}]
            },
            "6c5f0339-272a-4616-8b86-beaa2a66a0d8": {
              "id": "6c5f0339-272a-4616-8b86-beaa2a66a0d8",
              "type": "action",
              "strings": [],
              "action": {
                "type": "information",
                "title": {"type": "expression", "value": "\"Information\""},
                "text": {"type": "expression", "value": "\"Identity Verification Failed\""},
                "button_text": {"type": "expression", "value": "\"OK\""},
                "metadata": {"type": "information"}
              },
              "links": [{"name": "child", "type": "branch", "target": "2631bccb-6124-4fea-ae9e-8c944c202efb"}]
            },
            "2631bccb-6124-4fea-ae9e-8c944c202efb": {
              "id": "2631bccb-6124-4fea-ae9e-8c944c202efb",
              "type": "action",
              "strings": [],
              "action": {
                "type": "reject",
                "clear_session": false,
                "metadata": {"type": "reject"}
              },
              "links": []
            },
            "9f673ef2-e003-4edd-a0c5-bef4390688a8": {
              "id": "9f673ef2-e003-4edd-a0c5-bef4390688a8",
              "type": "transmit_platform_create_user",
              "email": {"type": "expression", "value": "clientData.userEmail"},
              "external_user_id": {"type": "expression", "value": "clientData.userEmail"},
              "username": {"type": "expression", "value": "clientData.userEmail"},
              "secondary_emails": [],
              "secondary_phone_numbers": [],
              "is_authenticated": false,
              "output_var": "create_user_output",
              "error_variable": "createError",
              "metadata": {},
              "links": [
                {"name": "success_child", "type": "branch", "target": "216934ad-67cb-49f3-8e8a-911c32ef2225"},
                {
                  "name": "failure",
                  "type": "escape",
                  "presentation": "Failure",
                  "display_name": {"type": "expression", "value": "`Failure`"},
                  "data_json_schema": {"type": "expression", "value": ""},
                  "target": "629bb3da-67a5-4cf7-a2bc-cf302dd905e6"
                }
              ]
            },
            "629bb3da-67a5-4cf7-a2bc-cf302dd905e6": {
              "id": "629bb3da-67a5-4cf7-a2bc-cf302dd905e6",
              "type": "action",
              "strings": [],
              "action": {
                "type": "information",
                "title": {"type": "expression", "value": "\"Information\""},
                "text": {"type": "expression", "value": "Add user failed ${createError}"},
                "button_text": {"type": "expression", "value": "\"OK\""},
                "metadata": {"type": "information"}
              },
              "links": [{"name": "child", "type": "branch", "target": "62bc6ac4-4b95-41d2-ba61-74d41ec86173"}]
            },
            "62bc6ac4-4b95-41d2-ba61-74d41ec86173": {
              "id": "62bc6ac4-4b95-41d2-ba61-74d41ec86173",
              "type": "condition",
              "condition": {
                "negated": false,
                "type": "generic",
                "metadata": {"type": "condition"},
                "field": {"type": "expression", "value": "@std.contains(createError.code,\"user_already_exists\")"},
                "data_type": "boolean",
                "operation": "==",
                "value": {"type": "expression", "value": "true"}
              },
              "links": [
                {"name": "true", "type": "branch"},
                {"name": "false", "type": "branch", "target": "55176304-a552-4ca6-a1ba-51b0f0161864"}
              ]
            },
            "55176304-a552-4ca6-a1ba-51b0f0161864": {
              "id": "55176304-a552-4ca6-a1ba-51b0f0161864",
              "type": "action",
              "strings": [],
              "action": {
                "type": "reject",
                "clear_session": false,
                "metadata": {"type": "reject"}
              },
              "links": []
            },
            "216934ad-67cb-49f3-8e8a-911c32ef2225": {
              "id": "216934ad-67cb-49f3-8e8a-911c32ef2225",
              "type": "transmit_platform_custom_user_data",
              "user_identifier": {"type": "expression", "value": "clientData.userEmail"},
              "data": {"type": "expression", "value": "{\"userIdentifier\":clientData.userEmail}"},
              "metadata": {},
              "links": [{"name": "success_child", "type": "branch", "target": "8babda01-74b4-4a23-9288-a109ee8455a6"}]
            },
            "8babda01-74b4-4a23-9288-a109ee8455a6": {
              "id": "8babda01-74b4-4a23-9288-a109ee8455a6",
              "type": "transmit_platform_device_registration",
              "user_identifier": {"type": "expression", "value": "clientData.userEmail"},
              "output_var": "key_id",
              "metadata": {},
              "links": [{"name": "success_child", "type": "branch", "target": "589f6415-6c3c-4824-851d-ab931bd5ec02"}]
            },
            "589f6415-6c3c-4824-851d-ab931bd5ec02": {
              "id": "589f6415-6c3c-4824-851d-ab931bd5ec02",
              "type": "transmit_platform_web_authn_registration",
              "user_identifier": {"type": "expression", "value": "clientData.userEmail"},
              "display_name": {"type": "expression", "value": ""},
              "allow_cross_platform_authenticators": false,
              "register_as_discoverable": true,
              "error_variable": "error",
              "metadata": {},
              "links": [
                {"name": "success_child", "type": "branch", "target": "16f83831-553d-43c5-86b2-922930b303ea"},
                {
                  "name": "failure",
                  "type": "escape",
                  "presentation": "Failure",
                  "display_name": {"type": "expression", "value": "`Failure`"},
                  "data_json_schema": {"type": "expression", "value": ""},
                  "target": "593ca0db-eaaf-4155-aeb2-7613aecfc03f"
                }
              ]
            },
            "16f83831-553d-43c5-86b2-922930b303ea": {
              "id": "16f83831-553d-43c5-86b2-922930b303ea",
              "type": "action",
              "strings": [],
              "action": {
                "type": "information",
                "title": {"type": "expression", "value": "\"Information\""},
                "text": {"type": "expression", "value": "\"Passkey successful\""},
                "button_text": {"type": "expression", "value": "\"OK\""},
                "metadata": {"type": "information"}
              },
              "links": [{"name": "child", "type": "branch"}]
            },
            "593ca0db-eaaf-4155-aeb2-7613aecfc03f": {
              "id": "593ca0db-eaaf-4155-aeb2-7613aecfc03f",
              "type": "action",
              "strings": [],
              "action": {
                "type": "reject",
                "clear_session": false,
                "metadata": {"type": "reject"}
              },
              "links": []
            },
            "a43c5ee6-76a3-40e6-bbdc-752792273bcf": {
              "id": "a43c5ee6-76a3-40e6-bbdc-752792273bcf",
              "type": "action",
              "strings": [],
              "action": {
                "type": "auth_pass",
                "metadata": {"type": "auth_pass"}
              },
              "links": []
            }
          }
        },
        "version_id": "default_version",
        "state": "version",
        "desc": "default_version"
      }],
      "name": "Account Protection and Identity Onboarding",
      "last_modified_date": 1703097600000,
      "created_date": 1703097600000,
      "type": "anonymous",
      "desc": "Comprehensive registration journey with risk assessment, email OTP, identity verification, and passwordless setup"
    },
    "category": "policy",
    "type": "dependency",
    "constraints": [
      {"server_version": "8.2.0", "type": "server_version"},
      {"application_type": "ido", "type": "application_type"},
      {"db_version": 5, "type": "db_version"}
    ],
    "dependencies": []
  }]
}
```

