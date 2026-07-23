n = list(input())
nr = list(reversed(n))
mae = []
usiro = []
for i in range(int((len(n)-1)/2)):
    mae.append(n[i])
    usiro.append(nr[i])

if mae == usiro:
    print('Yes')
else:
    print('No')
