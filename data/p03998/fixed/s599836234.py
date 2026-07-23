Sa = input()
Sb = input()
Sc = input()
l = [len(Sa), len(Sb), len(Sc)]
s = [Sa, Sb, Sc]
p = 0
while True:
    if l[p] <= 0:
        print("ABC"[p])
        break
    else:
        l[p] -= 1
        p = "abc".find(s[p][len(s[p])-l[p]-1])