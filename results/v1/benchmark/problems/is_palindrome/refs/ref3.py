def is_palindrome(s):
    def check(i, j):
        if i >= j:
            return True
        if not s[i].isalnum():
            return check(i + 1, j)
        if not s[j].isalnum():
            return check(i, j - 1)
        if s[i].lower() != s[j].lower():
            return False
        return check(i + 1, j - 1)
    return check(0, len(s) - 1)
