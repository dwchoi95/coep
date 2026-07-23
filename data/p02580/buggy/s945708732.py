from collections import Counter
from collections import defaultdict

def li():
    return [int(x) for x in input().split()]

H, W, M = li()
PH = []
PW = []

for i in range(M):
    h, w = li()
    PH.append(h)
    PW.append(w)

frequency_h_list = Counter(PH).most_common()
frequency_w_list = Counter(PW).most_common()
most_common_h_cnt = frequency_h_list[0][1]
most_common_w_cnt = frequency_w_list[0][1]

most_common_h_list = []
for x in frequency_h_list:
    if x[1] < most_common_h_cnt:
        break
    most_common_h_list.append(x[0])

most_common_w_list = []
for x in frequency_w_list:
    if x[1] < most_common_w_cnt:
        break
    most_common_w_list.append(x[0])

contain_intersection = {}
for h in most_common_h_list:
    for w in most_common_w_list:
        contain_intersection[h, w] = False

add = 0

for i in range(M):
    h, w = PH[i], PW[i]
    if h not in most_common_h_list and w not in most_common_w_list:
        continue
    if (h, w) not in contain_intersection:
        add = -1
        break
cnt = most_common_h_cnt + most_common_w_cnt + add

print(cnt)