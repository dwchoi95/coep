def cross(a,b):return a[0]*b[1] - a[1]*b[0]
        
n = int(input())
P =[]
s = 0
for i in range(n):P.append([int(i) for i in input().split()])
P = P*2
for i in range(n):s += cross(P[i],P[i+1])
print(abs(s)/2)