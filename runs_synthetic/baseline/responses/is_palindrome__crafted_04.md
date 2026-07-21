```python
def is_palindrome(s):
    t = "".join(c.lower() for c in s if c.isalnum())
    for k in range(len(t) // 2):
        if t[k] != t[-k - 1]:
            return False
    return True
```
