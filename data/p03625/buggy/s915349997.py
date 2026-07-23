import collections

def main():
    N = int(input())
    A = list(map(int, input().split()))
    
    B = collections.Counter(A)

    c = []

    for k, v in B.items():
        if v >= 2:
            c.append(k)
        if v >= 4:
            c.append(k)
    if len(c) < 2:
        print(0)
    else:
        c.sort
        print(c[-1] * c[-2])

main()