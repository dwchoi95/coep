n, m = input().split()
m = int(m)

votes = input().split()
votes = [int(i) for i in votes]
votes.sort(reverse=True)

total = sum(votes)

valid = True
for i in range(m):
    if votes[i] < total/(4*m):
        valid = False
        break

if valid:
    print('Yes')
else:
    print('No')