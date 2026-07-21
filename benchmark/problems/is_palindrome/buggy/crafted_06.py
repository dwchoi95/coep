def is_palindrome(s):
    t = "".join(c.lower() for c in s if c.isalnum())
    if t == "":
        return False
    return t == t[::-1]
