N,K=map(int, input().split())
S=input()
S=S.replace(S[K-1], chr(ord(S[K-1])+32))
print(S)