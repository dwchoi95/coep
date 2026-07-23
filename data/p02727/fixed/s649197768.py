x, y, a, b, c = map(int, input().split())
arrayP = list(map(int, input().split()))
arrayQ = list(map(int, input().split()))
arrayR = list(map(int, input().split()))
arrayP.sort(reverse=True)
arrayQ.sort(reverse=True)
arrayR.sort(reverse=True)
arrayAns = []
for i in range(x):
    arrayAns.append(int(arrayP[i]))
for i in range(y):
    arrayAns.append(int(arrayQ[i]))
arrayAns.sort()
for i in range(min(len(arrayR), len(arrayAns))):
    if arrayAns[i] <= int(arrayR[i]):
        arrayAns[i] = int(arrayR[i])
    else:
        break
print(sum(arrayAns))
