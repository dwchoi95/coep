import sys

length = int(sys.stdin.readline())
num_seq = sys.stdin.readline().split()
print(num_seq)

for i in range(1,length):
    print(num_seq[length - i],end=' ')
print(num_seq[0])
