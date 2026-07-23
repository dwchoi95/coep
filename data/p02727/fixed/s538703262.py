X, Y, A, B, C = map(int, input().split())
P = list(map(int, input().split()))
Q = list(map(int, input().split()))
R = list(map(int, input().split()))

P = sorted(P, reverse=True)[:X]
Q = sorted(Q, reverse=True)[:Y]
R = sorted(R, reverse=True)[:X+Y]

print(sum(sorted(P+Q+R, reverse=True)[:X+Y]))
