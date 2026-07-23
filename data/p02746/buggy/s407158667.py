
import math
Q = int(input())
A = [list(map(int, input().split())) for _ in range(Q)]



def measure(A):
    a,b,c,d = A
    if abs(a-c) < abs(b-d):
        s1, s2 = min([a,c]), max([a,c])
        l1, l2 = min([b,d]), max([b,d])
    else:
        l1, l2 = min([a,c]), max([a,c])
        s1, s2 = min([b,d]), max([b,d])
    min_K = int(math.log(s2-s1+1, 3) + 1)
    max_K = int(math.log(l2-l1+1, 3) + 1)
    for k in list(range(min_K, max_K+1))[::-1]:
        v = 3 ** k
        _l = 3 ** (k-1) + 1
        _h = (3 ** (k-1)) * 2
        c1 = s1
        c2 = (s1 % v <= _h) & (_l <= s1 % v)
        c3 = (s2 % v <= _h) & (_l <= s2 % v)
        if c1 & c2 & c3:
            val1 = (s1 % v - _l + 1) + (s2 % v - _l + 1) + (l2 - l1)
            val2 = (_h - s1 % v + 1) + (_h - s2 % v + 1) + (l2 - l1)
            print(min([val1, val2]))
            return None
    print(l2-l1+s2-s1)

if __name__ == '__main__':
    for val in A:
        measure(val)