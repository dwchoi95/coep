N,M=map(int,input().split())
cakes=[]
for i in range(N):
  x,y,z=map(int,input().split())
  cakes.append([x,y,z])
if M==0:
  print(0)
  quit()
score=[0]*8
score[0]=sum(sorted(map(lambda c: c[0]+c[1]+c[2], cakes))[-M:])
score[1]=sum(sorted(map(lambda c: c[0]+c[1]-c[2], cakes))[-M:])
score[2]=sum(sorted(map(lambda c: c[0]-c[1]+c[2], cakes))[-M:])
score[3]=sum(sorted(map(lambda c: c[0]-c[1]-c[2], cakes))[-M:])
score[4]=sum(sorted(map(lambda c:-c[0]+c[1]+c[2], cakes))[-M:])
score[5]=sum(sorted(map(lambda c:-c[0]+c[1]-c[2], cakes))[-M:])
score[6]=sum(sorted(map(lambda c:-c[0]-c[1]+c[2], cakes))[-M:])
score[7]=sum(sorted(map(lambda c:-c[0]-c[1]-c[2], cakes))[-M:])
print(max(score))
