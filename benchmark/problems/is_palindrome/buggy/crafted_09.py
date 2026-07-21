def is_palindrome(s):
    chars = [c.lower() for c in s if c.isalnum()]
    i = 0
    j = len(chars) - 1
    while i < j:
        if chars[i] != chars[j]:
            return False
        i += 1
    return True
