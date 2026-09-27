import torch, numpy as np, time, math
torch.set_num_threads(2)
dev = "cpu"
MCP=torch.tensor([9.3,38.]); PIP=torch.tensor([8.4,74.]); DIP=torch.tensor([7.5,105.])
R=7.0; A_=math.radians(225); B_=math.radians(315)

def make_chain(O1,O2):
    A0=O1+R*torch.tensor([math.cos(A_),math.sin(A_)]); B0=O2+R*torch.tensor([math.cos(B_),math.sin(B_)])
    return dict(o1x=O1[0].item(),o1y=O1[1].item(),o2x=O2[0].item(),o2y=O2[1].item(),L2=((B0-A0)**2).sum().item())
C1,C2=make_chain(MCP,PIP),make_chain(PIP,DIP)

def chain(t,c):
    ax=c['o1x']+R*torch.cos(A_-t); ay=c['o1y']+R*torch.sin(A_-t)
    dx=c['o2x']-ax; dy=c['o2y']-ay; d2=dx*dx+dy*dy
    K=(c['L2']-d2-R*R)/(2*R)
    return torch.atan2(dy,dx)-torch.acos((K*torch.rsqrt(d2)).clamp(-1,1))-B_
def analytic(t):
    p=chain(t,C1); return p, chain(p,C2)
analytic_c = torch.compile(analytic)

# LUT: gleichmaessiges Raster 0..90 Grad, 0.1 Grad Schritt
g=torch.linspace(0,math.radians(90),901); gp,gd=analytic(g); step=g[1]-g[0]
def lut_uniform(t):
    x=(t.clamp(0,g[-1])/step); i=x.floor().long().clamp(max=899); w=x-i
    return gp[i]+w*(gp[i+1]-gp[i]), gd[i]+w*(gd[i+1]-gd[i])
def lut_search(t):
    t=t.clamp(0,g[-1]); i=torch.searchsorted(g,t).clamp(1,900); w=(t-g[i-1])/(g[i]-g[i-1])
    return gp[i-1]+w*(gp[i]-gp[i-1]), gd[i-1]+w*(gd[i]-gd[i-1])

def bench(f,t,n=200):
    for _ in range(10): f(t)
    s=time.perf_counter()
    for _ in range(n): f(t)
    return (time.perf_counter()-s)/n*1e6
for N in (5, 4096*5, 16384*5):
    t=torch.rand(N)*math.radians(90)
    print(f"N={N:6d}  analytisch {bench(analytic,t):8.1f} us | analytisch compiled {bench(analytic_c,t):8.1f} us | "
          f"LUT gleichm. {bench(lut_uniform,t):8.1f} us | LUT searchsorted {bench(lut_search,t):8.1f} us")
t=torch.rand(100000)*math.radians(90)
a=torch.stack(analytic(t)); l=torch.stack(lut_uniform(t))
print("max. Fehler LUT (0.1 Grad Raster) [deg]:", torch.rad2deg((a-l).abs().max()).item())
