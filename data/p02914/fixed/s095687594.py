N = int(input())
A = [int(i) for i in input().split()]
 
s = 0
for i in range(N) :
    s ^= A[i]
    
for i in range(N) :
    A[i] &= ~s
 
r = 0
for i in range(60, -1, -1) :
    for j in range(r, N) :
        if (A[j] >> i) & 1 :
            A[r], A[j] = A[j], A[r]
            break
    else :
        continue
    
    for j in range(N) :
        if j == r :
            continue
        if (A[j] >> i) & 1 :
            A[j] ^= A[r]
    
    r += 1
    
ret = 0
for i in range(r) :
    ret ^= A[i]
    
print(ret * 2 + s)