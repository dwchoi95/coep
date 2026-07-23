def main():
    import sys
    def input(): return sys.stdin.readline().rstrip()
    n = int(input())
    a = list(map(int, input().split()))
    a = list(set(a))
    a_max = max(a)
    is_divable = [True]*(a_max+1)
    ans = 0
    is_divable[0],is_divable[1] = False,False
    for el in a:
        if is_divable[el]:
            ans +=1
            k = 2
            while k*el <= a_max:
                is_divable[k*el] = False
                k+=1
    print(ans)


if __name__ == '__main__':
    main()
