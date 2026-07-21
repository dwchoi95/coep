```python
def is_palindrome(s):
    t = "".join(c.lower() for c in s if c.isalnum())
    if t == "":
        return True
    return t == t[::-1]
```
