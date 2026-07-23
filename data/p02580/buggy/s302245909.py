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
 


leftkeys = (list(countleft.keys())[list(countleft.values()).index(leftmax)])
rightkeys = (list(countright.keys())[list(countright.values()).index(rightmax)])
 
leftkeyN = int(len(leftkeys))
rightkeyN = int(len(rightkeys))
flag = int(0)
cnt = int(0)

for i in range(leftkeyN):
    if flag != 0:
        break
    else:
        for P in range(rightkeyN):
            for T in range(M):
                if c[T] == [leftkeys[i],rightkeys[P]]:
                    cnt = cnt + 1
            if cnt == 0:
                flag = flag + 1
                break
            else:
                cnt = 0
 
if flag == 0:
    print(int(tempmax - 1))
else:
    print(int(tempmax))
    