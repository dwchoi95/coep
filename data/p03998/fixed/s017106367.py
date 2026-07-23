
import sys, math, fractions, itertools


def solve(S_A: str, S_B: str, S_C: str):
    t = 'a'
    A = list(S_A)
    B = list(S_B)
    C = list(S_C)
    a, b ,c = 0, 0, 0
    while(True):
        if t == 'a':
            if len(A) == a:
                w = 'A'
                break
            t = A[a]
            a += 1
        elif t == 'b':
            if len(B) == b:
                w = 'B'
                break
            t = B[b]
            b += 1
        else:
            if len(C) == c:
                w = 'C'
                break
            t = C[c]
            c += 1
    print(w)
    return



def main():
    def iterate_tokens():
        for line in sys.stdin:
            for word in line.split():
                yield word
    tokens = iterate_tokens()
    S_A = next(tokens)  
    S_B = next(tokens)  
    S_C = next(tokens)  
    solve(S_A, S_B, S_C)

if __name__ == '__main__':
    main()
