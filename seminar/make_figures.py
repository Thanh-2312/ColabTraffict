"""Generate vector figures directly from the audited model and benchmark data."""
from pathlib import Path
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'seminar/figures'
DATA=ROOT/'comparison_results/fair_benchmark_20261005_final'
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':12,'axes.spines.top':False,'axes.spines.right':False,'pdf.fonttype':42})
colors=['#68798b','#248f86','#2879b8','#8154b8']
methods=['Fixed-Time','MaxPressure','Q-Learning','Deep Q-Learning']
labels=['Fixed-Time','Max-Pressure','Q-Learning','DQN']
rows=json.loads((DATA/'test_results.json').read_text())
assert len(rows)==20
for m in methods:
 assert sorted(r['seed'] for r in rows if r['method']==m)==list(range(5001,5006))
for seed in range(5001,5006):
 rs=[r for r in rows if r['seed']==seed]
 assert len({r['demand_sha256'] for r in rs})==1
 assert all(r['requested']==r['created']+r['external_queue'] and not r['training'] and r['epsilon']==0 for r in rs)
train=json.loads((DATA/'training_log.json').read_text())
assert len(train)==40

def save(fig,name):
 fig.savefig(OUT/f'{name}.pdf',bbox_inches='tight',facecolor='white')
 fig.savefig(OUT/f'{name}.png',dpi=160,bbox_inches='tight',facecolor='white')
 plt.close(fig)

fig,ax=plt.subplots(figsize=(4.3,4.3))
ax.set(xlim=(-1.35,1.35),ylim=(-1.28,1.28),aspect='equal');ax.axis('off')
ax.add_patch(Rectangle((-1.03,-.19),2.06,.38,color='#dce3e9'))
ax.add_patch(Rectangle((-.19,-1.03),.38,2.06,color='#dce3e9'))
ax.plot([-1.03,1.03],[0,0],color='white',lw=2);ax.plot([0,0],[-1.03,1.03],color='white',lw=2)
ax.plot([.055,.055],[-1.03,1.03],color='#2879b8',lw=5,alpha=.85)
ax.plot([-1.03,1.03],[-.10,-.10],color='#b06c27',lw=3,ls='--')
ax.add_patch(Circle((0,0),.40,fill=False,ec='#248f86',lw=1.8,ls=':'))
for x,y in [(-.24,.24),(.24,.24),(.24,-.24),(-.24,-.24)]:
 ax.add_patch(Circle((x,y),.045,color='#17344b'));ax.add_patch(Circle((x,y),.023,color='#248f86'))
for x,y,s in [(0,1.16,'BẮC'),(0,-1.16,'NAM'),(1.2,0,'ĐÔNG'),(-1.2,0,'TÂY')]:ax.text(x,y,s,ha='center',va='center',fontweight='bold',fontsize=12)
ax.annotate('Cầu vượt B–N',(.055,.79),(.40,.97),fontsize=14,color='#2879b8',arrowprops={'arrowstyle':'-','color':'#2879b8'})
ax.annotate('Hầm Đ–T',(-.75,-.1),(-1.12,-.68),fontsize=14,color='#b06c27',arrowprops={'arrowstyle':'-','color':'#b06c27'})
ax.annotate('Vùng đếm xe',(.29,.29),(.49,.53),fontsize=14,color='#248f86',arrowprops={'arrowstyle':'-','color':'#248f86'})
ax.text(0,-1.4,'Sơ đồ chức năng; không theo tỷ lệ',ha='center',fontsize=9,color='#68798b')
save(fig,'network_map')

fig,ax=plt.subplots(figsize=(12,1.65));ax.axis('off');ax.set(xlim=(-.6,16.6),ylim=(-1.0,2.1))
for x,lane in enumerate(range(15,-1,-1)):
 c='#8154b8' if lane>=14 else '#2879b8' if lane>=12 else '#248f86' if lane>=4 else '#d89a37'
 ax.add_patch(Rectangle((x,.45),.95,.9,fc=c,ec='white'))
 ax.text(x+.47,.90,str(lane),color='white',ha='center',va='center',fontweight='bold',fontsize=13)
for x,lab,c in [(1,'Quay đầu\n14–15','#8154b8'),(3,'Rẽ trái\n12–13','#2879b8'),(8,'Đi thẳng\n4–11','#248f86'),(14,'Rẽ phải\n0–3','#b27919')]:
 ax.text(x,.13,lab,ha='center',va='top',fontsize=11,color=c)
ax.text(0,1.7,'PHÍA DẢI PHÂN CÁCH',fontsize=11,fontweight='bold',color='#17344b')
ax.text(16,1.7,'PHÍA LỀ PHẢI',ha='right',fontsize=11,fontweight='bold',color='#17344b')
save(fig,'sublanes')

fig,ax=plt.subplots(figsize=(9,3.9))
for i,m in enumerate(methods):
 vals=np.array([r['queue_mean'] for r in rows if r['method']==m]);mean=vals.mean()
 ax.bar(i,mean,color=colors[i],alpha=.8,width=.58)
 ax.errorbar(i,mean,yerr=vals.std(ddof=1),color='#17344b',capsize=5,fmt='none')
 ax.scatter(i+np.linspace(-.12,.12,5),vals,color='#17344b',s=20,zorder=3)
 ax.text(i,max(vals.max(),mean+vals.std(ddof=1))+2.0,f'{mean:.2f}',ha='center',fontweight='bold',fontsize=13)
ax.set_xticks(range(4),labels);ax.set_ylim(0,40);ax.set_ylabel('Số xe dừng trung bình');ax.grid(axis='y',alpha=.16);ax.set_axisbelow(True)
fig.tight_layout();save(fig,'test_queue')

fig,ax=plt.subplots(figsize=(9,3.9))
for i,m in enumerate(methods):
 rs=sorted([r for r in rows if r['method']==m],key=lambda r:r['seed'])
 ax.plot(range(5),[r['queue_mean'] for r in rs],'-o',label=labels[i],color=colors[i],lw=2)
ax.set_xticks(range(5),[str(n) for n in range(5001,5006)]);ax.set_ylabel('Số xe dừng trung bình');ax.set_xlabel('Seed kiểm tra');ax.legend(ncol=4,loc='upper center',bbox_to_anchor=(.5,1.21),frameon=False,fontsize=10);ax.grid(alpha=.17)
fig.tight_layout();save(fig,'test_seeds')

fig,ax=plt.subplots(figsize=(9,3.9))
validation=[]
for i,m in enumerate(methods[2:]):
 ys=[]
 for ep in [10,20,30,40]:
  rs=[json.loads((DATA/'validation'/f"ep{ep}_{m.replace(' ','_')}_{seed}"/'metrics.json').read_text()) for seed in [3001,3002]]
  y=np.mean([r['queue_mean'] for r in rs]);ys.append(y);validation.append({'episode':ep,'method':m,'queue_mean':float(y)})
 ax.plot([10,20,30,40],ys,'-o',color=colors[i+2],lw=2,label=labels[i+2])
 for ep,y in zip([10,20,30,40],ys):ax.annotate(f'{y:.1f}',(ep,y),xytext=(0,-16 if i==1 and ep in [20,30,40] else 8),textcoords='offset points',ha='center',fontsize=10)
ax.set_xticks([10,20,30,40]);ax.set_ylim(0,36);ax.set_xlabel('Số episode đã huấn luyện');ax.set_ylabel('Hàng đợi trên validation');ax.legend(frameon=False);ax.grid(alpha=.17)
fig.tight_layout();save(fig,'validation')
(DATA/'seminar_integrity_check.json').write_text(json.dumps({'train_episodes':40,'test_runs':20,'paired_demand':True,'frozen_evaluation':True,'demand_accounting':True},indent=2)+'\n')
(OUT/'data_summary.json').write_text(json.dumps({'training_last':train[-1],'validation':validation,'test':rows},indent=2)+'\n')
print(json.dumps({'transitions':train[-1]['transitions'],'updates':train[-1]['updates'],'validation':validation},indent=2))
