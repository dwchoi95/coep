import sys
input = sys.stdin.readline
a,b,c,d=map(str,input().split())

l=a+b
r=c+d
if l==r:
  print('Balanced')
elif l>r:
  print('Right')
else:
  print('Left')