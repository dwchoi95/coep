H,W,M = map(int,input().split())

h_target = [0]*(H+1)
w_target = [0]*(W+1)
target = []

for _ in range(M):
    h,w = map(int,input().split())
    target.append((h,w))
    h_target[h] += 1
    w_target[w] += 1

max_h_target = max(h_target)
max_w_target = max(w_target)

flag = False 

for i,j in target:
    if h_target[i] != max_h_target and w_target[j] != max_w_target:
        break
else:
    flag = True

if flag:
    print(max_h_target+max_w_target)
else:
    print(max_h_target+max_w_target-1)