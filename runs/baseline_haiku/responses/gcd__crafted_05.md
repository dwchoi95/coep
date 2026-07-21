```python
def gcd(a, b):
    if a == 0:
        return b
    if b == 0:
        return a
    best = 1
    for i in range(1, min(a, b) + 1):
        if a % i == 0 and b % i == 0:
            best = i
    return best
```
