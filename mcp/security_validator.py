#!/usr/bin/env python3
"""
Security Validator Module

Provides security validation functions for journey validation scripts.
Prevents path traversal attacks and ensures files are within allowed locations.
"""

import os
import sys
from pathlib import Path

# Security configuration
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_EXTENSIONS = [".json"]


def validate_path(file_path: str) -> None:
    """
    Validate that a file path is safe to access.

    Checks:
    - File is within workspace folder OR current working directory
    - File has allowed extension
    - File exists and is readable
    - File size is within limits

    Args:
        file_path: The file path to validate

    Raises:
        ValueError: If validation fails
        FileNotFoundError: If file doesn't exist
        PermissionError: If file isn't accessible
    """
    # Resolve to absolute path
    try:
        absolute_path = Path(file_path).resolve()
    except Exception as e:
        raise ValueError(f"Invalid path: {e}")

    # Get workspace folder (extension directory) and user's working directory (where gemini was invoked)
    workspace_folder = os.environ.get("WORKSPACE_FOLDER")
    user_cwd = os.environ.get("USER_CWD")  # Passed from Node.js server

    # Check if path is within either the workspace or user's working directory
    is_within_allowed_path = False

    if workspace_folder:
        try:
            absolute_workspace = Path(workspace_folder).resolve()
            absolute_path.relative_to(absolute_workspace)
            is_within_allowed_path = True
        except (ValueError, Exception):
            pass

    # Also allow files in the user's working directory (where gemini was invoked)
    if not is_within_allowed_path and user_cwd:
        try:
            absolute_user_cwd = Path(user_cwd).resolve()
            absolute_path.relative_to(absolute_user_cwd)
            is_within_allowed_path = True
        except (ValueError, Exception):
            pass

    if not is_within_allowed_path:
        raise ValueError(
            "Access denied: file must be within workspace or current directory"
        )

    # Check file extension
    if absolute_path.suffix.lower() not in ALLOWED_EXTENSIONS:
        raise ValueError(
            f"Access denied: only {', '.join(ALLOWED_EXTENSIONS)} files are allowed"
        )

    # Check file exists
    if not absolute_path.exists():
        raise FileNotFoundError(f"File not found: {absolute_path.name}")

    # Check file is readable
    if not os.access(absolute_path, os.R_OK):
        raise PermissionError(f"File not readable: {absolute_path.name}")

    # Check file is writable (needed for fixes)
    if not os.access(absolute_path, os.W_OK):
        raise PermissionError(f"File not writable: {absolute_path.name}")

    # Check file size
    file_size = absolute_path.stat().st_size
    if file_size > MAX_FILE_SIZE:
        raise ValueError(
            f"File too large: maximum size is {MAX_FILE_SIZE / (1024 * 1024)}MB"
        )


def sanitize_path_in_message(message: str, file_path: str) -> str:
    """
    Sanitize error messages to not expose full filesystem paths.

    Args:
        message: The error message to sanitize
        file_path: The file path to remove from the message

    Returns:
        Sanitized message with only filename
    """
    if not message:
        return message

    # Get just the filename
    filename = os.path.basename(file_path)

    # Replace full path with filename
    sanitized = message.replace(file_path, filename)

    # Also try to remove any other absolute paths
    sanitized = sanitized.replace(os.path.dirname(file_path) + "/", "")

    return sanitized


def validate_and_sanitize(file_path: str) -> str:
    """
    Validate path and return sanitized version for error messages.

    Args:
        file_path: The file path to validate

    Returns:
        The filename (for use in error messages)

    Raises:
        SystemExit: If validation fails (exits with code 1)
    """
    try:
        validate_path(file_path)
        return os.path.basename(file_path)
    except (ValueError, FileNotFoundError, PermissionError) as e:
        print(f"❌ Security validation failed: {e}", file=sys.stderr)
        sys.exit(1)
