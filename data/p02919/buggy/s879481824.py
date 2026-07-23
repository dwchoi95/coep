
import sys
INF = float("inf")


class MaxBit:
    def __init__(self, n):
        self.size = n
        self.tree = [0] * (n + 1)

    def sum(self, i):
        s = 0
        while i > 0:
            s = max(s, self.tree[i])
            i -= i & -i
        return s

    def add(self, i, x):
        while i <= self.size:
            self.tree[i] = max(self.tree[i], x)
            i += i & -i


class MinBit:
    def __init__(self, n):
        self.size = n
        self.tree = [n-1] * (n + 1)

    def sum(self, i):
        s = self.size-1
        while i > 0:
            s = min(s, self.tree[i])
            i -= i & -i
        return s

    def add(self, i, x):
        while i <= self.size:
            self.tree[i] = min(self.tree[i], x)
            i += i & -i


def solve(N: int, P: "List[int]"):

    prev = MaxBit(N+2)
    foll = MinBit(N+2)
    seq = [0]*(N+2)

    inv = {p: i for i, p in enumerate(P)}
    

    ans = 0
    for i in range(N, 0, -1):
        prev.add(inv[i]+2, inv[i]+1)
        foll.add(N-inv[i]+1, inv[i]+1)
        seq[inv[i]+1] = i

        
        
        
        
        
        p = prev.sum(inv[i]+1)
        pp = prev.sum(p)
        f = foll.sum(N-inv[i])
        ff = foll.sum(N-f+1)
        
        if p > 0:
            
            ans += i*(p - pp)
            
            ans += i*(f - (inv[i]+1))
            ans -= i
            
            
            
        
        if f < N+1:
            
            ans += i*(inv[i]+1 - p)
            
            ans += i*(ff - f)
            ans -= i
            
            
            
    print(ans)
    return


def main():

    def iterate_tokens():
        for line in sys.stdin:
            for word in line.split():
                yield word
    tokens = iterate_tokens()
    N = int(next(tokens))  
    P = [int(next(tokens)) for _ in range(N)]  
    solve(N, P)


if __name__ == '__main__':
    main()
