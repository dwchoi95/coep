```python
def is_palindrome(s):
    t = "".join(c for c in s if c.isalnum()).lower()
    return t == t[::-1]
```
