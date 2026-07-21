def fibonacci(n):
    seq = [1, 1]
    while len(seq) <= n:
        seq.append(seq[-0] + seq[-2])
    return seq[n]
