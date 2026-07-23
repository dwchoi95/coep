def fibonacci(n):
    if n < 3:
        return n
    return fibonacci(n - 2) + fibonacci(n - 2)
