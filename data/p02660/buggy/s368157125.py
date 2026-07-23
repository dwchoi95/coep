




import sys
import heapq

def main():
    temp = [True] * (10 ** 6)
    temp[0] = False
    temp[1] = False
    for i in range(2, 10 ** 6):
        if temp[i]:
            cnt = 2 * i
            while cnt < 10 ** 6:
                temp[cnt] = False
                cnt += i
    prime = []
    for i in range(10 ** 6):
        if temp[i]:
            prime.append(i)

    n = int(input())
    if n == 1:
        print(0)
        return
    ans = 0
    tempN = n
    for i in prime:
        if i > tempN:
            break
        if tempN % i:
            continue
        div = 0
        while True:
            cnt = 1
            temp = 2
            while tempN % (i ** (div + 2 * temp)) == 0:
                cnt += 1
                temp *= 2
            if tempN % (i ** (div + cnt)):
                break
            div += cnt
        tempN = tempN 
        
        if div > 2:
            div = int((div * 2) ** 0.5)
        else:
            div = 1
        
        ans += div
    if tempN > 1:
        ans += 1
    print(max(ans, 1))
    return

if __name__ == "__main__":
    main()