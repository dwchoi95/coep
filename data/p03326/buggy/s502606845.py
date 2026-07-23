import copy
n,m = map(int,input().split())


scores = list()
for i in range(n):
    score = list(map(int,input().split()))
    scores.append(score)

smax=None
for x in range(2):
    scores_=copy.deepcopy(scores)
    
    for i in range(n):
        scores_[i][0] = pow(-1,x)*scores[i][0]
    for y in range(2):
        for i in range(n):
            scores_[i][1] = pow(-1,x)*scores[i][1]
        for z in range(2):
            for i in range(n):
                scores_[i][2] = pow(-1,x)*scores[i][2]
        
            sumlist=list()
            for i in range(n):
                sumlist.append(sum(scores_[i]))
            sumlist.sort()
            tmp=0
            
            for eat in range(m):
                tmp+=sumlist[-1]
                sumlist.pop()
            if smax==None or tmp>smax:
                smax=tmp
print(smax)