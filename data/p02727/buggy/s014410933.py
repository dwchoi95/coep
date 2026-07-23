x,y,a,b,c= list(map(int,input().split()))

p = list(map(int,input().split()))
q = list(map(int,input().split()))
r = list(map(int,input().split()))
p.sort()
q.sort()
r.sort()

t=p[0:x] + q[0:y] + r
t.sort()
print(sum(t[0:(x+y)]))