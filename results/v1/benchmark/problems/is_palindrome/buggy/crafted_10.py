def is_palindrome(s):
    t = "".join(c.lower() for c in s if c.isalnum())
    half = len(t) // 2
    return t[:half] == t[half:]
