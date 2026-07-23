H,W,M = map(int,input().split())

h_target = [0]*(H+1)
w_target = [0]*(W+1)
target = []

for _ in range(M):
    h,w = map(int,input().split())
    target.append((h,w))
    h_target[h] += 1
    w_target[w] += 1

max_h = max(h_target)
max_w = max(w_target)

num_max_h = 0
num_max_w = 0

for i in h_target:
    if i == max_h:
        num_max_h += 1

for i in w_target:
    if i == max_w:
        num_max_w += 1

total = num_max_h*num_max_w
point = 0

for i,j in target:
    if h_target[i] == max_h and w_target[j] == max_w:
        point += 1

if point == total:
    print(max_h+max_w-1)
else:
    print(max_h+max_w)