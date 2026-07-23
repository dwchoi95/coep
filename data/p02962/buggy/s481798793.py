import sys
input = sys.stdin.readline
sys.setrecursionlimit(10 ** 7)

S = input().rstrip()
T = input().rstrip()


LS = len(S)
LT = len(T)
n = (LT + (-LT) % LS) 
S *= (n+1)
S = S[:LS+LT]

MOD = 10 ** 9 + 7
base = 1234
base_inv = pow(base,MOD-2,MOD) 
power = [1] * (LS+LT)
power_inv = [1] * (LS+LT)
for n in range(1,LS+LT):
    power[n] = power[n-1] * base % MOD
    power_inv[n] = power_inv[n-1] * base_inv % MOD

def to_rolling_hash(S):
    ret = [0] * len(S)
    prev = 0
    for i,s in enumerate(S):
        x = (prev + power[i] * ord(s)) % MOD
        ret[i] = x
        prev = x
    return ret

S_hash = to_rolling_hash(S) + [0]
T_hash = to_rolling_hash(T)[-1] 

can_start = [(S_hash[i + LT - 1] - S_hash[i - 1]) * power_inv[i] % MOD == T_hash for i in range(LS)]
