a,b,c = map(int, input().split())
x0=c
x1=a*c-b
x2=a*(x1-x0)+x1
x3=a*(x2-x1)+x2
x4=a*(x3-x2)+x3
x5=a*(x4-x3)+x4
x6=a*(x5-x4)+x5
x7=a*(x6-x5)+x6
x8=a*(x7-x6)+x7
x9=a*(x8-x7)+x8
x10=a*(x9-x8)+x9

print(x1)
print(x2)
print(x3)
print(x4)
print(x5)
print(x6)
print(x7)
print(x8)
print(x9)
print(x10)