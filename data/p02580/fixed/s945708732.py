from collections import Counter
from collections import defaultdict

def li():
    return [int(x) for x in input().split()]

H, W, M = li()
PH = []
PW = []
PHF = defaultdict(int)
PWF = defaultdict(int)
PF = defaultdict(int)

for i in range(M):
    h, w = li()
    PH.append(h)
    PW.append(w)
    PHF[h] += 1
    PWF[w] += 1
    PF[h, w] += 1

sorted_PHF = sorted(PHF.items(), key=lambda x: x[1], reverse=True)
sorted_PWF = sorted(PWF.items(), key=lambda x: x[1], reverse=True)
most_common_h_cnt = sorted_PHF[0][1]
most_common_w_cnt = sorted_PWF[0][1]

most_common_h_list = []
for x in sorted_PHF:
    if x[1] < most_common_h_cnt:
        break
    most_common_h_list.append(x[0])

most_common_w_list = []
for x in sorted_PWF:
    if x[1] < most_common_w_cnt:
        break
    most_common_w_list.append(x[0])

add = -1
for h in most_common_h_list:
    for w in most_common_w_list:
        if PF[h, w] == 0:
            add = 0
            break

cnt = most_common_h_cnt + most_common_w_cnt + add

print(cnt)