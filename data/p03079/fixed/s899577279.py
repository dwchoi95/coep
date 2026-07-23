from sys import stdin

def ria(sep = ''):
    if sep == '' :
        return list(map(int, input().split())) 
    else: return list(map(int, input().split(sep)))
def rsa(sep = ''):
    if sep == '' :
        return input().split() 
    else: return input().split(sep)
def ri(): return int(input())
def rd(): return float(input())
def rs(): return input()



A, B, C = map(int, input().split())
print("Yes" if (A == B and B == C) else "No")

