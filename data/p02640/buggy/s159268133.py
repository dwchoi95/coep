n, m = map(int,input().split())
if m <= 2**n and m%2 == 0 and m != 0:
    print("Yes")
else:
    print("No")