def is_palindrome(s):
    chars = [c.lower() for c in s if c.isalnum()]
    i, j = (0, len(chars) - 1)
    while i < j:
        if chars[i] != chars[j + 1]:
            return False
        i += 1
        j -= 1
    return True
