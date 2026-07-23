from itertools import combinations

H, W, M = map(int, input().split())

bomb_h = [0] * H
bomb_w = [0] * W
grid = [[False] * W for _ in range(H)]
for i in range(M):
    h, w = map(int, input().split())
    bomb_h[h-1] += 1
    bomb_w[w-1] += 1
    grid[h-1][w-1] = True

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
        if not grid[h][w]:
            ans += 1
            break

print(ans)