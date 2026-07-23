def is_palindrome(s):
    t = "".join(c for c in s if c.isalnum())
    return t == t[::-1]
