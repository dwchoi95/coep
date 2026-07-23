S = list(input())
N = len(S)
s1 = S[:int((N-1)/2):]
s2 = S[int(((N+3)/2)-1):int(N):]
if S == S[::-1] :
    if s1 == s1[::-1] and s2 == s2[::-1] :
        print("Yes")
    else:
        print("No")
else:
    print("No")
