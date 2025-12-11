import string
import secrets
from typing import Optional

def generate_random_password(
    length: int = 4,
    include_uppercase: bool = True,
    include_digits: bool = True,
    include_symbols: bool = False,
    # Characters excluded to prevent issues in URLs, databases, or terminal display
    exclude_chars: Optional[str] = 'lIO0o\'"\\`$%^&*()[]{}<>/|~',
) -> str:
    """
    Generates a cryptographically secure random password.

    Args:
        length (int): The desired length of the password. Default is 4.
        include_uppercase (bool): Include uppercase letters (A-Z).
        include_digits (bool): Include digits (0-9).
        include_symbols (bool): Include a defined set of safe symbols (e.g., @#+,-_!).
        exclude_chars (Optional[str]): A string of characters to explicitly exclude.
                                       Defaults exclude ambiguous and problematic characters.

    Returns:
        str: The generated random password.
    
    Raises:
        ValueError: If the required character sets cannot meet the specified length.
    """
    
    # Define the character sets
    lowercase = string.ascii_lowercase
    uppercase = string.ascii_uppercase if include_uppercase else ''
    digits = string.digits if include_digits else ''
    # Defining a subset of safe, non-ambiguous symbols that are generally URL/database safe
    safe_symbols = r'@#!-+=' if include_symbols else ''
    
    # Combine all requested character sets
    all_characters = lowercase + uppercase + digits + safe_symbols

    # Remove excluded characters from the pool
    if exclude_chars:
        # Create a set of characters to keep (all_characters minus exclude_chars)
        all_characters = ''.join(c for c in all_characters if c not in exclude_chars)

    # Check if the remaining pool is large enough or if the length is too short
    if not all_characters:
        raise ValueError("Character pool is empty after exclusions.")
    if length <= 0:
        raise ValueError("Password length must be a positive integer.")

    # Ensure at least one character from each requested set is included (for strength)
    # This prevents edge cases where a random selection might not include a digit, for example.
    required_chars = []
    
    if include_uppercase and uppercase:
        required_chars.append(secrets.choice(uppercase))
    if include_digits and digits:
        required_chars.append(secrets.choice(digits))
    if include_symbols and safe_symbols:
        required_chars.append(secrets.choice(safe_symbols))

    # The remaining length is the total length minus the required characters
    remaining_length = length - len(required_chars)
    
    if remaining_length < 0:
        raise ValueError("Password length is too short to include all required character types.")

    # Fill the rest of the password length with random choices from the full pool
    random_part = [secrets.choice(all_characters) for _ in range(remaining_length)]
    
    # Combine required and random parts
    password_list = required_chars + random_part
    
    # Shuffle the list to randomize the position of the required characters
    secrets.SystemRandom().shuffle(password_list)
    
    return "".join(password_list)

# --- Example Usage ---
"""
# 1. Standard, secure password (16 characters, uppercase, lowercase, digits)
secure_pwd = generate_random_password(length=16)
print(f"Standard Secure Password (16 chars): {secure_pwd}")

# 2. RADIUS/Hotspot safe password (10 characters, URL/Database friendly)
# This is a good choice for your MikroTik application
hotspot_pwd = generate_random_password(length=10, include_symbols=False)
print(f"Hotspot Safe Password (10 chars, no symbols): {hotspot_pwd}")

# 3. Short 6-character code (e.g., for single-use PIN)
code_6char = generate_random_password(length=6, include_symbols=False, include_uppercase=True, include_digits=True)
print(f"6-Character Code (no symbols or uppercase): {code_6char}")
"""