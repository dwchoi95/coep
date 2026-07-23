

import sys

















from heapq import heapify, heappush, heappop 







from operator import itemgetter              




def main():
    mod = 1000000007                
    inf = float('inf')              
    
    sys.setrecursionlimit(10**6)    
    def input(): return sys.stdin.readline().rstrip()
    def ii():    return int(input())
    def mi():    return map(int, input().split())
    def mi_0():  return map(lambda x: int(x)-1, input().split())
    def lmi():   return list(map(int, input().split()))
    def lmi_0(): return list(map(lambda x: int(x)-1, input().split()))
    def li():    return list(input())
    
    
    n = ii()
    L = lmi()
    
    left = sum(L[:n])
    l_h = L[:n]    
    heapify(l_h)

    right = 0
    tmp = [[i, L[i]] for i in range(n, 3*n)]
    assert (len(tmp) == 2*n)
    tmp.sort(key=itemgetter(1))
    latter_min_nth = [False] * 3 * n    
    sub_member_r_h = []    
    for ind in range(n):
        i, num = tmp[ind]
        right += num
        latter_min_nth[i] = True
    for ind in range(n, 2*n):
        i, num = tmp[ind]
        sub_member_r_h.append([num, i])
    heapify(sub_member_r_h)        
    

    max_score = left - right
    
    for i in range(n, 2*n):
        
        if l_h[0] < L[i]:
            
            left -= heappop(l_h)
            left += L[i]
            heappush(l_h, L[i])
        if latter_min_nth[i]:
            
            latter_min_nth[i] = False
            right -= L[i]
            while sub_member_r_h[0][1] <= i:
                heappop(sub_member_r_h)    
            num, ind = heappop(sub_member_r_h)
            assert (ind > i)
            right += num
            latter_min_nth[ind] = True
        
        max_score = max(max_score, left - right)
    
    print(max_score)


if __name__ == "__main__":
    main()



