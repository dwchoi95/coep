def is_palindrome(s):
    t = s.replace(" ", "").lower()
    return t == t[::-1]
