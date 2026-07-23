def fibonacci(n):
    seq = [0, 1]
    while len(seq) <= n:
        seq.append(seq[-1] + seq[-1])
    return seq[n]
