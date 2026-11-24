import json,datetime as dt,sys
START=dt.date(2026,10,15)
JORNADA=8*60
# feriados Fortaleza (nacionais, estaduais CE, municipais) 2026-2027
FER={
 '2026-10-12':'Nossa Senhora Aparecida (nacional)','2026-11-02':'Finados (nacional)','2026-11-15':'Proclamação da República (nacional)',
 '2026-11-20':'Consciência Negra (nacional)','2026-12-25':'Natal (nacional)',
 '2027-01-01':'Confraternização Universal (nacional)','2027-03-19':'São José (estadual)','2027-03-25':'Data Magna do Ceará (estadual)',
 '2027-03-26':'Sexta-feira Santa (nacional)','2027-04-21':'Tiradentes (nacional)','2027-05-01':'Dia do Trabalho (nacional)',
 '2027-05-27':'Corpus Christi (municipal)','2027-08-15':'Nossa Senhora da Assunção (municipal)','2027-09-07':'Independência (nacional)',
 '2027-10-12':'Nossa Senhora Aparecida (nacional)','2027-11-02':'Finados (nacional)','2027-11-15':'Proclamação da República (nacional)',
 '2027-11-20':'Consciência Negra (nacional)','2027-12-25':'Natal (nacional)'}
HO_DEFAULT=[2]  # quarta (Mon=0)
# equipes e regra de home office (seg=0)
EQUIPES={'Pedagógico':{'ho':[],'chapas':['00021','00038','00040']},
 'Desenvolvimento':{'ho':[1,3],'chapas':['00030']},
 'Design':{'ho':[2,3],'chapas':['00012']}}
EQUIPE_EXTRA={'00001':'Administrativo','00023':'Comercial','00016':'CS','00036':'Marketing'}
SEM_HO=set()
FALTAS={}  # {'00030':['2026-10-27',...]} só quando informado
def equipe(ch):
    for n,e in EQUIPES.items():
        if ch in e['chapas']:return n,e['ho']
    if ch in SEM_HO:return EQUIPE_EXTRA.get(ch,'Área não informada'),[]
    return EQUIPE_EXTRA.get(ch,'Área não informada'),HO_DEFAULT
APELIDO={}
def m(t):h,mi=t.split(':');return int(h)*60+int(mi)
def dedupe(ps):
    out=[]
    for p in ps:
        if out and m(p)-m(out[-1])<=3: continue
        out.append(p)
    return out
def run(months_files,out):
    emps={};months=[]
    for mf in months_files:
        raw=json.load(open(mf));ym=None
        for chapa,e in raw.items():
            eq,ho=equipe(chapa);emps.setdefault(chapa,{'chapa':chapa,'nome':e['nome'],'ho':ho,'equipe':eq})
        # month range from first date
        any_d=next(iter(raw.values()))['dias'][0]['data'];d0=dt.datetime.strptime(any_d,'%d/%m/%Y').date()
        first=d0.replace(day=1);nxt=(first+dt.timedelta(days=32)).replace(day=1);last=nxt-dt.timedelta(days=1)
        ym=first.strftime('%Y-%m');mrec={'mes':ym,'inicio':max(first,START).isoformat(),'fim':last.isoformat(),'colab':{}}
        for chapa,e in raw.items():
            byd={dt.datetime.strptime(x['data'],'%d/%m/%Y').date():x for x in e['dias']}
            ho=emps[chapa]['ho'];days=[];tot={'esperado':0,'trabalhado':0,'saldo':0,'ho':0,'just':0,'inc':0,'presenca':0,'extra_fds':0,'faltas':0,'entradas':[]}
            d=max(first,START)
            while d<=last:
                key=d.isoformat();wd=d.weekday();rec=byd.get(d);ps=dedupe(rec['p']) if rec else []
                util=wd<5 and key not in FER
                day={'d':key,'wd':wd,'p':ps,'tipo':None,'trab':None,'esp':0,'saldo':0,'fer':FER.get(key)}
                if util:
                    day['esp']=JORNADA
                if not util:
                    if ps and len(ps)%2==0:
                        w=sum(m(ps[i+1])-m(ps[i]) for i in range(0,len(ps),2))
                        if len(ps)==2 and w>360:w-=60
                        day.update(tipo='extra',trab=w,saldo=w);tot['extra_fds']+=w
                    elif ps: day.update(tipo='incompleto');tot['inc']+=1
                    else: day['tipo']='folga' if not day['fer'] else 'feriado'
                elif wd in ho:
                    day.update(tipo='ho',trab=JORNADA,saldo=0);tot['ho']+=1
                elif not rec:
                    day.update(tipo='normal',trab=JORNADA,saldo=0);tot['presenca']+=1
                elif key in FALTAS.get(chapa,[]):
                    day.update(tipo='falta',trab=0,saldo=-JORNADA);tot['faltas']+=1
                elif not ps:
                    day.update(tipo='justificado',trab=JORNADA,saldo=0);tot['just']+=1
                elif len(ps)%2==1:
                    day.update(tipo='incompleto',trab=None,saldo=0,esp=0);tot['inc']+=1
                else:
                    w=sum(m(ps[i+1])-m(ps[i]) for i in range(0,len(ps),2))
                    if len(ps)==2 and w>360:w-=60
                    day.update(tipo='ponto',trab=w,saldo=w-JORNADA);tot['presenca']+=1
                    tot['entradas'].append(m(ps[0]))
                if day['tipo'] in('ponto','normal','ho','justificado','falta'):
                    tot['esperado']+=JORNADA;tot['trabalhado']+=day['trab']
                tot['saldo']+=day['saldo']
                days.append(day);d+=dt.timedelta(days=1)
            ent=tot.pop('entradas');tot['entrada_media']=round(sum(ent)/len(ent)) if ent else None
            mrec['colab'][chapa]={'tot':tot,'dias':days}
        months.append(mrec)
    # acumulado
    acc={c:0 for c in emps}
    for mr in months:
        for c,v in mr['colab'].items():
            v['tot']['anterior']=acc[c];acc[c]+=v['tot']['saldo'];v['tot']['acumulado']=acc[c]
    REGRAS={'jornada_semanal_h':40,'jornada_diaria_min':JORNADA,'inicio_acompanhamento':START.isoformat(),
 'almoco':{'desconto_min':60,'quando':'só entrada e saída registradas e período acima de 6h'},
 'marcacao_duplicada_min':3,
 'home_office':'conta 8h cumpridas, mesmo com ponto batido no dia',
 'home_office_padrao':HO_DEFAULT,'equipes':{n:{'ho':e['ho'],'chapas':e['chapas']} for n,e in EQUIPES.items()},
 'sem_home_office':sorted(SEM_HO),'area_por_chapa':EQUIPE_EXTRA,
 'fora_do_relatorio':{'Desenvolvimento':['Iuri','Alex']},
 'dia_sem_marcacao':'conta como jornada cumprida; vira falta (débito de 8h) só quando informada',
 'faltas_informadas':FALTAS,
 'dia_util_fora_do_relatorio':'jornada cumprida',
 'marcacao_incompleta':'fora do saldo e em alerta até corrigir',
 'dia_nao_util_trabalhado':'entra inteiro como crédito (com desconto de almoço acima de 6h)',
 'feriados':'nacionais, estaduais (CE) e municipais (Fortaleza); pontos facultativos contam como dia útil',
 'acumulado':'saldo de cada mês somado aos meses anteriores'}
    import time
    json.dump({'revisao':int(time.time()),'regras':REGRAS,'equipes':{n:{'ho':e['ho']} for n,e in EQUIPES.items()},'faltas':FALTAS,'gerado':dt.date.today().isoformat(),'inicio':START.isoformat(),'jornada':JORNADA,'feriados':FER,'colaboradores':list(emps.values()),'meses':months},open(out,'w'),ensure_ascii=False)
    for c,v in months[-1]['colab'].items(): 
        t=v['tot'];print(c,emps[c]['nome'][:28].ljust(28),'saldo',t['saldo'],'acum',t['acumulado'],'inc',t['inc'],'just',t['just'],'ho',t['ho'],'pres',t['presenca'])
if __name__=='__main__': run(sys.argv[2:],sys.argv[1])
