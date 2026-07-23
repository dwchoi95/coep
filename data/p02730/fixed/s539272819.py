n = list(input())

mae = []
usiro = []
for i in range(int((len(n)-1)/2)):
    mae.append(n[i])
for i in range(int((len(n)+3)/2)-1,len(n)):
    usiro.append(n[i])

if mae == usiro:
    print('Yes')
else:
    print('No')
