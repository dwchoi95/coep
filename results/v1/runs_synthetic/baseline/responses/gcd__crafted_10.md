```python
def gcd(a, b):
    if b == 0:
        return a
    while a % b != 0:
        temp = b
        b = a % b
        a = temp
    return b
```
