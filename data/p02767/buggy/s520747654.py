def resolve():
    import math
    n = int(input())
    x = list(map(int,input().split()))
    b =  math.ceil(sum(x)/n)
    m = 0
    for i in x:
        m += (i-b) * (i-b)
    print(m)
resolve()