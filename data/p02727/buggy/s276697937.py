x,y,a,b,c = map(int,input().split())
pl = list(map(int,input().split()))
ql = list(map(int,input().split()))
rl = list(map(int,input().split()))

pp = sorted(pl,reverse=True)[:x-1]
qq = sorted(pl,reverse=True)[:y-1]
all = pp + qq + rl
print(sum(sorted(pl,reverse=True)[:x+y-1]))