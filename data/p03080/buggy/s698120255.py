n=int(input())
s=input()

if n - len([i for i in s if i == 'R']) > 0:
    print('Yes')
else:
    print('No')