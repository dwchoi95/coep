
import sys, math, fractions, itertools, collections, copy, heapq


def solve(S: str):
    counter = 0
    tmp = S[0]
    for s in S[1:]:
        if s == tmp[-1]:
            tmp = tmp + s
        elif s == 'W' and tmp[-1] == 'B':
            tmp = tmp + s
        else:
            counter += 2 * min(tmp.count('B'), tmp.count('W'))
            tmp = s
    counter += 2 * min(tmp.count('B'), tmp.count('W'))
    print(counter)
    return



def main():
    def iterate_tokens():
        for line in sys.stdin:
            for word in line.split():
                yield word
    tokens = iterate_tokens()
    S = next(tokens)  
    solve(S)

if __name__ == '__main__':
    main()
