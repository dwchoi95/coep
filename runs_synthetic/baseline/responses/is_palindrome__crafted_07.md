```python
def is_palindrome(s):
    t = "".join(c.lower() for c in s if c.isalnum())
    rev = ""
    for c in t:
        rev = c + rev
    return rev == t
```
