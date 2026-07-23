


n = int(input())
a_inputs = list(map(int,input().split()))

all_pair = 1
odd_pair = 1

for i in range(n):
    if a_inputs[i]%2==0:
        odd_pair*=2
    else:
        odd_pair*=1
    all_pair*=3

print(all_pair-odd_pair)


