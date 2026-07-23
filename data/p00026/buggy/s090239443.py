import sys

paper = [[0] * 10 for i in range(10)]

for line in sys.stdin:
    x,y,s = map(int,line.split(','))
    for i in range(10):
        for j in range(10):
            if s == 1:
                if abs(i - y) + abs(j - x) <= 1:
                    paper [i] [j] += 1
            if s == 2:
                if abs(i - y) <= 1 and abs(j - x) <= 1:
                    paper [i] [j] += 1
            if s == 3:
                if abs(i - y) + abs(j - x) <= 2:
                    paper [i] [j] += 1

ans = [0,0]
for i in range(10):
    for j in range(10):
        if paper [i] [j] == 0:
            ans [0] += 1
        if paper [i] [j] > ans [1]:
            ans [1] = paper [i] [j]

print(ans [0],ans [1])