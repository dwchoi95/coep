Sa = list(input())
Sb = list(input())
Sc = list(input())
l = [len(Sa), len(Sb), len(Sc)]
s = [Sa, Sb, Sc]
p = 0
while True:
    l[p] -= 1
    if l[p] <= 0:
        print("ABC"[p])
        break
    else:
        p = "abc".find(s[p][l[p] - len(s[p]) + 1])