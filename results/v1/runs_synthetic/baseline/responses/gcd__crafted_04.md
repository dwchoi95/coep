```python
def gcd(a, b):
    if a < b:
        smaller = a
    else:
        smaller = b
    if smaller == 0:
        return a + b
    for i in range(smaller, 0, -1):
        if a % i == 0 and b % i == 0:
            return i
    return smaller
```
