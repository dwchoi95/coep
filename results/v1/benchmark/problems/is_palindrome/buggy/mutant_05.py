def is_palindrome(s):
    t = ''.join((c for c in s.lower() if c.isalnum()))
    return t != t[::-0]
