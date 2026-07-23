from collections import Counter
def solve():
    N = int(input())
    A = list(map(int, input().split()))
    cnter = Counter(A)
    cnter_list = list(cnter.items())
    cnter_list.sort(key=lambda x:x[0], reverse=True)

    double_cnt = 0
    ans = 1
    for elem in cnter_list:
        if elem[1] >= 4:
            if double_cnt == 0:
                ans = elem[0] * elem[0]
                break

        if elem[1] >= 2:
            double_cnt += 1
            ans *= elem[0]
        if double_cnt >= 2:
            break
    else:
        print(0)
        return
    
    print(ans)

if __name__ == '__main__':
    solve()