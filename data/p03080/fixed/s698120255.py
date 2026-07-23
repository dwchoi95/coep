n=int(input())
s=input()

if len([i for i in s if i == 'R']) * 2 - n > 0:
    print('Yes')
else:
    print('No')
