import sys
input = sys.stdin.buffer.readline

H, W, M = map(int, input().split())

bomb_h = [0] * H
bomb_w = [0] * W
bomb = set()
for i in range(M):
    h, w = map(int, input().split())
    bomb_h[h-1] += 1
    bomb_w[w-1] += 1
    bomb.add((h-1, w-1))

max_h = max(bomb_h)
max_w = max(bomb_w)

h_indices = []
for i in range(H):
    if bomb_h[i] == max_h:
        h_indices.append(i)

w_indices = []
for i in range(W):
    if bomb_w[i] == max_w:
        w_indices.append(i)

ans = max_w + max_h - 1
for h in h_indices:
    for w in w_indices:
        if (h, w) not in bomb:
            ans += 1
            print(ans)
            exit()

if ans == -1:
    ans = 0

print(ans)
