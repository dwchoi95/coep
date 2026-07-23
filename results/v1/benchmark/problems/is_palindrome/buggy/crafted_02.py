def is_palindrome(s):
    t = s.lower()
    return t == t[::-1]
