a = input().split()
S = int(a[0])
W = int(a[1])
if S <= W:
    print("unsafe")
else:
    print("safe")