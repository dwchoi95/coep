import math
def check(n):
    count = 0
    end = int(math.sqrt(n)+1)
    for i in range(2,end):
        if n%i==0:
            count += 1
            n/=i
        if n%i==0:
            l = 2
            count2 = 0
            while n%i==0:
                n/=i
                count2+=1
                if count2==l:
                    count+=1
                    count2=0
                    l+=1
        if n==1:
            return count
    if n==1:
        return 0
    if count==0:
        return 1
    else:
        return count+1   
n = int(input())
ans = check(n)
print(ans)