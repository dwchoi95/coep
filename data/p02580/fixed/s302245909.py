import collections
a = input().split()
M = int(a[2])
hidari = []
migi = []
c = []
 
for i in range(M):
  b = input().split()
  hidari.append(b[0])
  migi.append(b[1])
  c.append(b)
  
countleft = collections.Counter(hidari)
countright = collections.Counter(migi)
leftmax = countleft.most_common()[0][1]
rightmax = countright.most_common()[0][1]
tempmax = int(leftmax + rightmax)
 
leftkeys = [k for k, v in countleft.items() if v == leftmax]
rightkeys = [k for k, v in countright.items() if v == rightmax]
 
leftkeyN = int(len(leftkeys))
rightkeyN = int(len(rightkeys))
flag = int(0)
cnt = int(0)



 
for i in range(M):
    goukei = int(countleft.get(c[i][0])) + int(countright.get(c[i][1]))
    if goukei == tempmax:
        cnt += 1
    else:
        pass

if cnt == int(leftkeyN * rightkeyN):
    print(int(tempmax - 1))
else:
    print(int(tempmax))