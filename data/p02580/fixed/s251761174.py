

h, w, m = map(int, input().split())
hw_array = [list(map(int, input().split())) for _ in range(m)]

h_array = [0]*h
w_array = [0]*w

for hw in hw_array:
    h, w = hw
    h_array[h - 1] += 1
    w_array[w - 1] += 1

h_max = max(h_array)
h_argmax_array = [True if i == h_max else False for i in h_array]
w_max = max(w_array)
w_argmax_array = [True if j == w_max else False for j in w_array]

comb = sum(h_argmax_array) * sum(w_argmax_array)
for hw in hw_array:
    h, w = hw
    if h_argmax_array[h - 1] and w_argmax_array[w - 1]:
        comb -= 1
ans = h_max + w_max
if comb == 0:
    ans -= 1

print(ans)