INPUT = input().split()
r = int(INPUT[0])
D = int(INPUT[1])
X = int(INPUT[2])

XX = []

ans = ""
XX.append(X)

i = 0
while i <= 10:
    v = r * XX[i] - D
    XX.append(v)
    ans = ans + str(XX[i + 1]) + '\n'
    i += 1

print(ans)