S = input()
N = len(S)
SF_num = int((N-1)/2)
SF = S[:SF_num]
SF_rev = SF[::-1]
SB = S[-SF_num:]
SB_rev = SB[::-1]

if SF == SB_rev:
    if SF[:SF_num] == SF_rev[:SF_num]:
        if SB[-SF_num:] == SB_rev[-SF_num:]:
            print("Yes")
else:
    print("No")