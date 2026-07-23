N = int(input())
S = input()
tmp = ''
count = 0
for s in S:
    if s != tmp:
        count += 1
    tmp = s
print(count)