H, W, M = map(int, input().split())

H_bom = [0 for i in range(H)]
W_bom = [0 for i in range(W)]
bom_map = [[0 for i in range(W)] for i in range(H)]

for i in range(M):
    M_temp = list(map(int, input().split()))
    H_bom[M_temp[0]-1] += 1
    W_bom[M_temp[1]-1] += 1
    bom_map[M_temp[0]-1][M_temp[1]-1] = 1


H_bom_max = max(H_bom)
W_bom_max = max(W_bom)
H_bom_line = []
W_bom_line = []

for i in range(H):
    if H_bom[i] == H_bom_max:
        H_bom_line.append(i)
for i in range(W):
    if W_bom[i] == W_bom_max:
        W_bom_line.append(i)

bom_check_flag = 0

for i in H_bom_line:
    for j in W_bom_line:
        if bom_map[i-1][j-1] == 1:
            print(H_bom_max + W_bom_max)
            bom_check_flag = 1
            break
if bom_check_flag == 0:
    print(H_bom_max + W_bom_max -1)
