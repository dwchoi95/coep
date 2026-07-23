x, y, a, b, c = map(int, input().split())
arrayP = list(input().split())
arrayQ = list(input().split())
arrayR = list(input().split())
arrayP.sort(reverse=True)
arrayQ.sort(reverse=True)
arrayR.sort(reverse=True)
arrayAns = []
for i in range(x):
    arrayAns.append(int(arrayP[i]))
for i in range(y):
    arrayAns.append(int(arrayQ[i]))
arrayAns.sort()
for i in range(len(arrayR)):
    if arrayAns[0] <= int(arrayR[i]):
        arrayAns[0] = int(arrayR[i])
        arrayAns.sort()
print(sum(arrayAns))