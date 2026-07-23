
X, Y, A, B, C = map(int,input().split())
p0 = list(map(int,input().split()))
q0 = list(map(int,input().split()))
r0 = list(map(int,input().split()))
p = sorted(p0, reverse = True); p.append(0)
q = sorted(q0, reverse = True); q.append(0)
r = sorted(r0, reverse = True); r.append(0)

happy = 0
i = 0
j = 0
k = 0
red = 0
green = 0
white = 0

for _ in range(X+Y):
    if max(p[i], q[j], r[k]) == r[k]:
        happy += r[k]
        white += 1
        k += 1
    elif max(p[i], q[j], r[k]) == p[i]:
        if red < X:
            happy += p[i]
            red += 1
            i += 1
        elif q[j] >r[k] and green < Y:
            happy += q[j]
            green += 1
            j += 1
        else:
            happy += r[k]
            white += 1
            k += 1
    else:
        if green < Y:
            happy += q[j]
            green += 1
            j += 1
        elif p[i] >r[k] and red < X:
            happy += p[i]
            red += 1
            i += 1
        else:
            happy += r[k]
            white += 1
            k += 1
            
print(happy)