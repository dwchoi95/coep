

def main():
    N = int(input())
    t = list(map(int, input().split()))
    a = list(reversed(list(map(int, input().split()))))

    m = [0] * N

    b = 0
    for i,h in enumerate(t):
        if b != h:
            m[i] = h
        b = h
    b = 0
    for j,h in enumerate(a):
        if b != h:
            if m[N-j-1] != 0 and m[N-j-1] != h:
                print(0)
                return
            else:
                m[N-j-1] = h
        b = h
    res = 1
    for k,h in enumerate(m):
        if h == 0:
            print(a[N-k-1], t[k])
            res = res * min(a[N-k-1], t[k]) % (pow(10, 9) + 7)
    print(res)

main()
