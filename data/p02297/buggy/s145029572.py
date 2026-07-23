from sys import stdin
readline = stdin.readline


def dot(a, b):
    return a.real * b.real + a.imag * b.imag


def triangle(a, b, c):
    v1, v2 = b - a, c - a
    s = abs(v1) ** 2 * abs(v2) ** 2 - dot(v1, v2) ** 2
    return s ** 0.5 * 0.5


def polygon(p):
    return sum(triangle(p[0], pi, pj) for pi, pj in zip(p[1:], p[2:]))


n = int(readline())
p = [map(int, readline().split()) for _ in range(n)]
p = [x + y * 1j for x, y in p]
print('{:.1f}'.format(polygon(p)))