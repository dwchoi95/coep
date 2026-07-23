def get_result(A):
    res = 1
    total = 3 ** len(A)
    for i, ai in enumerate(A):
        res *= 2 if ai % 2 == 0 else 1
    return total - res
n = input()
A = [int(ai) for ai in input().split()]
print(get_result(A))