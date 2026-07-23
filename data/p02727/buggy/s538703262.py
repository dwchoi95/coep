X, Y, A, B, C = map(int, input().split())
P = list(map(int, input().split()))
Q = list(map(int, input().split()))
R = list(map(int, input().split()))

P = sorted(P, reverse=True)[:X]
Q = sorted(P, reverse=True)[:Y]
R = sorted(P, reverse=True)[:X+Y]

print(sum(sorted(P+Q+R, reverse=True)[:X+Y]))
