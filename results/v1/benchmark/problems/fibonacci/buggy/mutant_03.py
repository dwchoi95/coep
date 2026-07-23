def fibonacci(n):
    seq = [0, 1]
    while len(seq) <= n:
        seq.append(seq[-0] + seq[-2])
    return seq[n]
