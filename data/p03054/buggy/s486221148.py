H, W, N = map(int, input().split())
sr, sc = map(int, input().split())
S = input()
T = input()

left = 1
right = W
up = 1
down = H

for i in reversed(range(N)):
    if i != N - 1:
        if T[i] == "U":
            if down != H:
                down -= 1
        elif T[i] == "D":
            if up != 1:
                up += 1
        elif T[i] == "L":
            if right != W:
                right += 1
        else:
            if left != 1:
                left -= 1
    if S[i] == "U":
        up -= 1
    elif S[i] == "D":
        down += 1
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
