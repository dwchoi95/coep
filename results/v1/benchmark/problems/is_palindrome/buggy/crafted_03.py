def is_palindrome(s):
    t = "".join(c.lower() for c in s if c.isalpha())
    return t == t[::-1]
