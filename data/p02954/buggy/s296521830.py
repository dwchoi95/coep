S=input()
ans = [0] * len(S)
last_R=[0] * len(S)
tmp = 0
for i in range(len(S)):
    if S[i] == "R":
        tmp = i
    last_R[i] = tmp
first_L=[0] * len(S)
tmp = 0
for i in reversed(range(len(S))):
    if S[i] == "L":
        tmp = i
    first_L[i] = tmp
for i in range(len(S)):
    if S[i] == "L":
        R_index = last_R[i]
        if i - R_index % 2 == 1:
            ans[R_index+1] += 1
        else:
            ans[R_index] += 1
    if S[i] == "R":
        L_index = first_L[i]
        if L_index - i %2 == 1:
            ans[L_index-1] += 1
        else:
            ans[L_index] += 1
ans = map(str, ans)
print(" ".join(ans))