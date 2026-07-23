H, W, M = map(int, input().split())

H_bomb = [0 for i in range(H)]
W_bomb = [0 for i in range(W)]
bomb_list = []

for i in range(M):
    M_temp = tuple(map(int, input().split()))
    H_bomb[M_temp[0]-1] += 1
    W_bomb[M_temp[1]-1] += 1
    bomb_list.append(M_temp)


H_bomb_max = max(H_bomb)
W_bomb_max = max(W_bomb)
H_bomb_line = []
W_bomb_line = []

for i in range(H):
    if H_bomb[i] == H_bomb_max:
        H_bomb_line.append(i)
for i in range(W):
    if W_bomb[i] == W_bomb_max:
        W_bomb_line.append(i)

bomb_set = set(bomb_list)
for i in H_bomb_line:
    for j in W_bomb_line:
        if (i+1, j+1) not in bomb_set:
            print(H_bomb_max + W_bomb_max)
            exit()
print(H_bomb_max + W_bomb_max - 1)
