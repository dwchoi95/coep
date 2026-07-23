n=int(input())

x=[]
y=[]
for _ in range(n):
    xx,yy=map(int,input().split())
    x.append(xx)
    y.append(yy)

def maxAbsValExpr(arr1, arr2):
    minX, maxX = min(arr1), max(arr1)
    minY, maxY = min(arr2), max(arr2)
    
    ans = 0
    
    for point in [(minX, minY), (maxX, minY), (minX, maxY), (maxX, maxY)]:
        minD = float('inf')
        maxD = float('-inf')
        for i in range(0, len(arr1)):
            distance = abs(arr1[i]-point[0]) + abs(arr2[i]-point[1]) + i
            minD = min(minD, distance)
            maxD = max(maxD, distance)
            ans = max(ans, maxD - minD)
    return ans


print(maxAbsValExpr(x, y)-1)

