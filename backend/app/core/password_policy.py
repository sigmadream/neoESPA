from __future__ import annotations

import string

MIN_PASSWORD_LENGTH = 10
MAX_PASSWORD_LENGTH = 128


def validate_password(password: str) -> str:
    """Validate passwords accepted by every account-creation/reset path."""
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError(
            f"Password must be at least {MIN_PASSWORD_LENGTH} characters long"
        )
    if len(password) > MAX_PASSWORD_LENGTH:
        raise ValueError(
            f"Password must be at most {MAX_PASSWORD_LENGTH} characters long"
        )
    if any(character.isspace() for character in password):
        raise ValueError("Password must not contain whitespace")

    character_classes = (
        any(character.islower() for character in password),
        any(character.isupper() for character in password),
        any(character.isdigit() for character in password),
        any(character in string.punctuation for character in password),
    )
    if sum(character_classes) < 2:
        raise ValueError(
            "Password must contain at least two of lowercase letters, "
            "uppercase letters, numbers, and symbols"
        )
    return password
