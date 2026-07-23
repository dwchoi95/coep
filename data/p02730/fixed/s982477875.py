S = input()
N = len(S)
SF_num = int((N-1)/2)
SF = S[:SF_num]
SF_rev = SF[::-1]
SB_num = int((N+3)/2)
SB = S[SB_num-1:]
SB_rev = SB[::-1]

if SF == SB_rev and SF == SF_rev and SB == SB_rev:
    print("Yes")
else:
    print("No")