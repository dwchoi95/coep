N = int(input())
a = [int(x) for x in input().split()]
count = 0
if (N==len(a))and(2<=N):
    for i in range(1,N-1):
        if (a[i-1]==a[i]):
            a[i] += 1
            if a[i] > 10000:
                a[i] = 1
            if a[i]==a[i+1]:
                a[i] += 1
                if a[i] > 10000:
                    a[i] = 1
            count += 1
    print(count)