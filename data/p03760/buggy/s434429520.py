O = input()
E = input()
print(*[o+e for o,e in zip(O,E)], sep="")
