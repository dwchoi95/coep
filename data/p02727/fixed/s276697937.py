import heapq
x,y,a,b,c = map(int,input().split())
pl = list(map(int,input().split()))
ql = list(map(int,input().split()))
rl = list(map(int,input().split()))

pp = sorted(pl,reverse=True)[:x]
qq = sorted(ql,reverse=True)[:y]
al = pp + qq + rl

print(sum(sorted(al,reverse=True)[:x+y]))