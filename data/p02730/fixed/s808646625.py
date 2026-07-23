S = input()
N = len(S)

if S != S[::-1]:
    print('No')
    exit(0)


cond_1 = S[:int((N-1)/2)]
cond_1_r = cond_1[::-1]

if cond_1 != cond_1_r:
    print('No')
    exit(0)

cond_2 = S[int((N+3)/2-1):]
cond_2_r = cond_2[::-1]

if cond_2 != cond_2_r:
    print('No')
    exit(0)

print('Yes')
