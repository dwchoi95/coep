def resolve():
    n = int(input())
    x = list(map(int,input().split()))
    b =  round(sum(x)/n)
    m = 0
    for i in x:
        m += (i-b) * (i-b)
    print(m)
resolve()