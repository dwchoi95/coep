
import sys

def solve(N: int, W: int, w: "List[int]", v: "List[int]"):
    from itertools import groupby, product
    base_w = w[0]
    v_list = [[] for _ in range(4)]
    for ww, vv in zip(w, v):
        v_list[ww-base_w].append(vv)
    v_list = [sorted(vv, reverse=True) for vv in v_list]
    acc_v = [[0] for _ in range(4)]
    for i, vv in enumerate(v_list):
        for vvv in vv:
            acc_v[i].append(acc_v[i][-1] + vvv)
    ans = 0
    for i, j, k, l in product(*[range(len(a)) for a in acc_v]):
        if i * base_w + j * (base_w + 1) + k * (base_w + 2)+ l * (base_w + 3) > W:
            continue
        ans = max(ans, acc_v[0][i] + acc_v[1][j] + acc_v[2][k] + acc_v[3][l])
    return ans


def main():
    def iterate_tokens():
        for line in sys.stdin:
            for word in line.split():
                yield word
    tokens = iterate_tokens()
    N = int(next(tokens))  
    W = int(next(tokens))  
    w = [int()] * (N)  
    v = [int()] * (N)  
    for i in range(N):
        w[i] = int(next(tokens))
        v[i] = int(next(tokens))
    print(solve(N, W, w, v))

def test():
    import doctest
    doctest.testmod()

if __name__ == '__main__':
    
    main()
