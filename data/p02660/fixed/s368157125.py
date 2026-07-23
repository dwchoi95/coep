




import sys
import heapq

def main():
    temp = [True] * (10 ** 6 + 10)
    temp[0] = False
    temp[1] = False
    for i in range(2, 10 ** 6 + 10):
        if temp[i]:
            cnt = 2 * i
            while cnt < 10 ** 6 + 10:
                temp[cnt] = False
                cnt += i
    prime = []
    for i in range(10 ** 6 + 10):
        if temp[i]:
            prime.append(i)
 
    n = int(input())
    ans = 0
    tempN = n
    for i in prime:
        if i > tempN:
            break
        if tempN % i:
            continue
        div = 0
        while tempN % i == 0:
            tempN = tempN 
            div += 1
        tempAns = int((div * 2) ** 0.5)
        if tempAns * (tempAns + 1) 
            tempAns -= 1
        
        ans += tempAns
    if tempN > 1:
        ans += 1
    print(ans)
    return
 
if __name__ == "__main__":
    main()