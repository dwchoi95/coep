```python
def sum_digits(n):
    count = 0
    while n > 0:
        count += n % 10
        n //= 10
    return count
```
