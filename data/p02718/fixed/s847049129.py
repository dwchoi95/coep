N,M = map(int,input().split())

votos = list(map(int,input().split()))

qtd_votos = sum(votos)

minimo = qtd_votos/(4*M)

votos.sort(reverse = True)

if votos[M-1] >= minimo:
    print("Yes")
else:
    print("No")
