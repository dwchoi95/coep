S = input()
ans = [0]*len(S)
tmp = []
cnt = 1;

for i in range(len(S)-1):
  if(S[i] == S[i+1]):
    cnt += 1
  else:
    tmp.append(cnt)
    cnt = 1
tmp.append(cnt)

cnt = 0
for i in range(len(tmp)-1):
  cnt += tmp[i]
  if(i % 2 == 0):
    if((tmp[i] - tmp[i+1])%2 == 0):
      ans[cnt-1] = int((tmp[i]+tmp[i+1])/2)
      ans[cnt] = int((tmp[i]+tmp[i+1])/2)
    else:
      if(abs(tmp[i] - tmp[i+1]) > 2):
        if(tmp[i] > tmp[i+1]):
          ans[cnt-1] = int((tmp[i] + tmp[i+1]-1)/2)
          ans[cnt] = int((tmp[i]+tmp[i+1]+1)/2)
        else:
          ans[cnt-1] = int((tmp[i] + tmp[i+1]+1)/2)
          ans[cnt] = int((tmp[i]+tmp[i+1]-1)/2)
      else:
        if(tmp[i] > tmp[i+1]):
          ans[cnt-1] = int((tmp[i] + tmp[i+1]+1)/2)
          ans[cnt] = int((tmp[i]+tmp[i+1]-1)/2)
        else:
          ans[cnt-1] = int((tmp[i] + tmp[i+1]-1)/2)
          ans[cnt] = int((tmp[i]+tmp[i+1]+1)/2)
        
print(*ans)