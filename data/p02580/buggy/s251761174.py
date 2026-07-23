

h, w, m = map(int, input().split())
hw_array = [list(map(int, input().split())) for _ in range(m)]

h_array = [0]*h
w_array = [0]*w

for hw in hw_array:
    h, w = hw
    h_array[h - 1] += 1
    w_array[w - 1] += 1

h_max = max(h_array)
h_argmax_array = [i for i in h_array if i == h_max]
w_max = max(w_array)
w_argmax_array = [j for j in w_array if j == w_max]

flag = False
for h_argmax in h_argmax_array:
    for w_argmax in w_argmax_array:
        if not [h_argmax + 1, w_argmax + 1] in hw_array:
            flag = True
            break

ans = h_max + w_max
if not flag:
    ans -= 1

print(ans)