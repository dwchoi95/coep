s = input()
w = int(input())

length = len(s)

output = s[0]
i = w

while(i<length):
    output += s[i]
    i += w

print(output)