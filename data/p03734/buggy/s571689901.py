N,W = map(int,input().split())
dic = {"0":[],"1":[],"2":[],"3":[]}
for i in range(N):
  w,v = map(int,input().split())
  if i == 0:
    Min = w
  if w == Min:
    dic["0"].append(v)
  elif w == Min+1:
    dic["1"].append(v)
  elif w == Min+2:
    dic["2"].append(v)
  elif w == Min+3:
    dic["3"].append(v)
    
dic["0"].sort()
dic["1"].sort()
dic["2"].sort()
dic["3"].sort()

ans = 0
for i in range(len(dic["0"])+1):
  for j in range(len(dic["1"])+1):
    for k in range(len(dic["2"])+1):
      for l in range(len(dic["3"])+1): 
        a = int(sum(dic["0"][:i])+sum(dic["1"][:j])+sum(dic["2"][:k])+sum(dic["3"][:l])) 
        b = int(i*Min+j*(Min+1)+k*(Min+2)+l*(Min+3))
        if a > ans and b <= W:
          ans = a
print(int(ans))