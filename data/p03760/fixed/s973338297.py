
O = input()
E = input()

for o, e in zip(O, E):
    print(o + e, end="")
if abs(len(O) - len(E)) == 1:
    print(O[-1])