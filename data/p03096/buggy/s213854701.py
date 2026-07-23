
import sys

MOD = 1000000007  

def solve(N, C):
    last = [-1] * (N + 1)
    pairs = []
    for i, c in enumerate(C):
        try:
            prev = last[c - 1]
        except:
            if c > N:
                return
            else:
                raise Exception()
        if prev >= 0 and prev < i - 1:
            pairs.append((prev, i))
        last[c - 1] = i
    print(0)
    return
    pairs.sort()
    count = [0] * N
    count[0] = 1
    idx = 0
    for i in range(N):
        if i > 0:
            count[i] += count[i - 1]
            count[i] %= MOD
        while idx < len(pairs) and pairs[idx][0] == i:
            count[pairs[idx][1]] += count[i]
            count[pairs[idx][1]] %= MOD
            idx += 1
    print(count[N - 1])
    return



def main():
    def iterate_tokens():
        for line in sys.stdin:
            for word in line.split():
                yield word
    tokens = iterate_tokens()
    N = int(next(tokens))  
    C = [ int(next(tokens)) for _ in range(N) ]  
    solve(N, C)

if __name__ == '__main__':
    main()
