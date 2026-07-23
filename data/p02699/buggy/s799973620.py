S, W = map(int, input().split())
S = int(S / 2)

if S < W:
    print("unsafe")
else:
    print("safe")