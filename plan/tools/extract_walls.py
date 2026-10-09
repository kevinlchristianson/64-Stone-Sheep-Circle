import pdfplumber, sys, json
pdf = pdfplumber.open(sys.argv[1]); p = pdf.pages[0]
EXT=(0.537254929, 0.60784316, 0.713725507); INT=(0.890196084, 0.815686285, 0.384313732)
rs=[r for r in p.rects if r.get('non_stroking_color') in (EXT,INT)]
x0=min(r['x0'] for r in rs); y0=min(r['top'] for r in rs)
print('origin pt', x0, y0)
f=lambda v: round(v/18,3)
out=[]
for r in sorted(rs,key=lambda r:(r['top'],r['x0'])):
  k='E' if r['non_stroking_color']==EXT else 'I'
  out.append((k,f(r['x0']-x0),f(r['top']-y0),f(r['x1']-x0),f(r['bottom']-y0)))
for o in out: print(o[0], o[1:], 'w=%.3f h=%.3f'%(o[3]-o[1],o[4]-o[2]))
json.dump({'origin':[x0,y0],'rects':out},open('walls.json','w'))
# white rects (windows/doors openings?) 
wh=[r for r in p.rects if r.get('non_stroking_color')==(1.0,1.0,1.0)]
print('white', len(wh))
for r in sorted(wh,key=lambda r:(r['top'],r['x0'])): print('W',f(r['x0']-x0),f(r['top']-y0),f(r['x1']-x0),f(r['bottom']-y0))
cy=[r for r in p.rects if r.get('non_stroking_color')==(0.68235296, 1.0, 1.0)]
for r in cy: print('CY',f(r['x0']-x0),f(r['top']-y0),f(r['x1']-x0),f(r['bottom']-y0))
