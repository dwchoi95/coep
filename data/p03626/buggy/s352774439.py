N = int(input())
S1 = input()
S2 = input()
patterns = []
flag = False
for i in range(N):
    if S1[i] == S2[i]:
        patterns.append('row')
    elif flag is False:
        patterns.append('column')
        flag = True
    else:
        flag = False

print(patterns)
if patterns[0] == 'row':
    count = 3
else:
    count = 6
for i in range(1, len(patterns)):
    prev = patterns[i-1]
    current = patterns[i]
    if prev == 'row':
        if current == 'row':
            count *= 2
        else:
            count *= 2
    else: 
        if current == 'row':
            count *= 1
        else:
            count *= 3
print(count % (10**9  + 7))