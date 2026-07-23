```python
def is_palindrome(s):
    t = "".join(c.lower() for c in s if c.isalnum())
    for i in range(len(t) // 2):
        if t[i] != t[len(t) - 1 - i]:
            return False
    return True
```
