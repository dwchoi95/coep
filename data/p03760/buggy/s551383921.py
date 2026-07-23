

o = list(input())
e = list(input())

if len(o) == len(e):
    for i in range(len(o) - 1):
        print(o[i], end = '')
        print(e[i], end = '')
    print(o[len(o) - 1], end = '')
    print(e[len(e) - 1])

for i in range(min(len(o), len(e))):
    print(o[i], end = '')
    print(e[i], end = '')
if len(e) > len(o):
    print(e[len(e) - 1])
if len(o) < len(e):
    print(o[len(o) - 1])
