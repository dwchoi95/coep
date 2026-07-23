def main():
    import sys
    def input(): return sys.stdin.readline().rstrip()
    n = int(input())
    a = list(map(int, input().split()))
    a.sort()
    a_max = a[-1]
    is_divisible = [True]*(a_max+1)
    ans = 0
    is_divisible[0]= False
    el_old = 0
    for el in a:
        if is_divisible[el]:
            if el == el_old:
                ans-=1
                is_divisible[el] = False
                continue
            ans +=1
            k = 2
            while k*el <= a_max:
                is_divisible[k*el] = False
                k+=1
        el_old = el
    print(ans)


if __name__ == '__main__':
    main()
