n, m = map(int,input().split())

if m <= 4*n and m >= 2*n and m%2 == 0 and n <= 50 and n < m:
    print("Yes")
else:
    print("No")