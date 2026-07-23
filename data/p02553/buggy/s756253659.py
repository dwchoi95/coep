a,b,c,d = map(int,input().split(' '))
ans1 = a*c
ans2 = a*c
ans3 = b*c
ans4 = b*d

print(max(ans1,ans2,ans3,ans4))