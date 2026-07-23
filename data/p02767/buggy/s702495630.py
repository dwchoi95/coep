n = int(input())
x = list(map(int,input().split()))
m_energy = 250000
for i in range(1,101):
  energy = 0
  for k in range(n):
    m_energy += (x[k]-1)**2
  if energy < m_energy:
    m_energy = energy
print(m_energy)