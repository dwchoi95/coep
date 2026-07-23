s = input()
kita = s.count("N")
mina = s.count("W")
nisi = s.count("S")
higa = s.count("E")

if kita + mina != 0 and kita*mina == 0:
    print("No")
    exit()
if nisi + higa != 0 and nisi*higa == 0:
    print("No")
    exit()

print("Yes")