def is_palindrome(s):
    chars = [c.lower() for c in s if c.isalnum()]
    i, j = (1, len(chars) - 2)
    while i < j:
        if chars[i] != chars[j]:
            return False
        i += 1
        j -= 1
    return True
