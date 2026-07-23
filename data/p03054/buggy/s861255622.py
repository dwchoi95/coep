H, W, N = map(int, input().split())
sr, sc = map(int, input().split())
S = input()
T = input()

left = 0
right = W
up = 0
down = H

for i in reversed(range(N)):
    if i != N - 1:
        if T[i] == "U":
            down = min(H, down+1)
        elif T[i] == "D":
            up = max(0, up-1)
        elif T[i] == "L":
            right = min(W, right+1)
        else:
            left = max(0, left-1)
    if S[i] == "U":
        up += 1
    elif S[i] == "D":
        down -= 1
    elif S[i] == "L":
        left += 1
    else:
        right -= 1
    if left == right or up == down:
        print("NO")
        exit()


if left <= sr <= right and up <= sc <= down:
    print("YES")
else:
    print("NO")
