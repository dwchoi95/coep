N,M = map(int,input().split())

votos = list(map(int,input().split()))

qtd_votos = sum(votos)
minimo = qtd_votos

contador = 0
for i in votos:
    if i > minimo:
        contador += 1
if contador >= M:
    print("Yes")
else:
    print("No")
