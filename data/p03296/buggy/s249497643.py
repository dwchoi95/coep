iN = int(input())
aS = [int(x) for x in input().rstrip().split()]



iCounter = 0
if iN == 2:
    if aS[0] == aS[1]:
        iCounter += 1
else:
    for i in range(1,iN-1):
        if aS[i] == aS[i-1]:
            if aS[i] == aS[i+1]:
                if aS[i] != 10000:
                    aS[i] += 1
                else:
                    aS[i] -= 1
                iCounter += 1
            else:
                if i == iN - 2:
                    continue
                else:
                    iU = max(aS[i],aS[i+1])
                    if iU < 10000:
                        iU += 1
                    else:
                        iU -= 1
                        if iU == min(aS[1],aS[i+1]):
                            iU -= 1
                    aS[i] = iU
                    iCounter += 1
print(iCounter)
