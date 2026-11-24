import re,json,sys
txt=open(sys.argv[1],encoding='utf-8').read().splitlines()
emp=None;out={};cur=None
rx=re.compile(r'^(\d\d/\d\d/\d{4}) (\S+)\s+(.*)$')
for ln in txt:
    m=re.match(r'Chapa: (\d+) - (.+)$',ln.strip())
    if m: emp=(m.group(1),m.group(2).strip());out.setdefault(emp[0],{'nome':emp[1],'dias':[]});continue
    m=rx.match(ln)
    if m and emp:
        d,dow,rest=m.groups()
        # columns: punches up to ~col 78, then faltas atraso extra
        left=ln[:78];right=ln[78:]
        punches=re.findall(r'\d\d:\d\d',left[len(d)+4:])
        nums=re.findall(r'\d\d:\d\d',right)
        cur={'data':d,'dow':dow,'p':punches,'falta':nums[0] if len(nums)>0 else None,'atraso':nums[1] if len(nums)>1 else None,'extra':nums[2] if len(nums)>2 else None,'hor':None,'just':''}
        out[emp[0]]['dias'].append(cur);continue
    m=re.match(r'\s*Horário:\s*(.*)$',ln)
    if m and cur: cur['hor']=re.findall(r'\d\d:\d\d',m.group(1))
    m=re.match(r'\s*Justificativa:\s*(.*)$',ln)
    if m and cur and m.group(1).strip(): cur['just']=m.group(1).strip()
json.dump(out,open(sys.argv[2],'w'),ensure_ascii=False,indent=1)
