n, m = map(int, input().split())
lis = [list(map(int, input().split())) for i in range(n)]

def arr_multiply( lis2):
    def inner(lis1):
        return sum([l1*l2 for l1, l2 in zip(lis1, lis2)])
    return inner

max_score = 0
if m == 0:
    print(0)
else:
    for a in (-1, 1):
        for b in (-1, 1):
            for c in (-1, 1):
                func = arr_multiply([a, b, c])
                score = sum(sorted(list(map(func, lis)))[-m:])
                if score > max_score:
                    max_score = score
    print(max_score)