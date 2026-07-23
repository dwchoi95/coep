from sys import stdin
data = stdin.readlines()

n = int(data[0].split()[0])
a = [int(s) for s in data[1].split()]
a = sorted(a)

max = a[-1]
print(max)

l = [0]*(max+1)

for i in a:
    l[i] += 1
    if l[i] == 1:
        for j in range(i*2,max+1,i):
            l[j] = 2
print(l.count(1))