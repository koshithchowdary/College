def analyze(x):
    z=x.iloc[-1]; score=50; reasons=[]; blockers=[]; changes=[]; direction=None
    if z.trend=='bullish': score+=12; reasons.append('20 EMA above 50 EMA: bullish regime')
    elif z.trend=='bearish': score+=12; reasons.append('20 EMA below 50 EMA: bearish regime')
    else: score-=10; blockers.append('No clear trend')
    if z.displacement: score+=10; reasons.append('Displacement confirms momentum')
    else: score-=5; blockers.append('No displacement confirmation'); changes.append('Wait for decisive displacement')
    if z.relative_volume>=1.2: score+=8; reasons.append('Volume above recent average')
    else: score-=8; blockers.append('Weak volume'); changes.append('Require stronger relative volume')
    if z.trend=='bullish' and z.liquidity_sweep_low: direction='BUY'; score+=15; reasons.append('Sell-side liquidity sweep aligned with trend')
    elif z.trend=='bearish' and z.liquidity_sweep_high: direction='SELL'; score+=15; reasons.append('Buy-side liquidity sweep aligned with trend')
    else: blockers.append('No aligned liquidity sweep'); changes.append('Wait for aligned liquidity sweep')
    if direction=='BUY' and z.delta_proxy>0 or direction=='SELL' and z.delta_proxy<0: score+=8; reasons.append('Estimated Delta confirms direction')
    elif direction: score-=10; blockers.append('Estimated Delta does not confirm'); changes.append('Wait for order-flow confirmation')
    score=max(0,min(100,int(score))); entry=float(z.Close); atr=max(float(z.atr),entry*.002)
    if direction=='BUY': stop=entry-1.2*atr; risk=entry-stop; targets=[entry+1.5*risk,entry+2.5*risk,entry+4*risk]
    elif direction=='SELL': stop=entry+1.2*atr; risk=stop-entry; targets=[entry-1.5*risk,entry-2.5*risk,entry-4*risk]
    else: stop=None; targets=[None]*3
    status=direction if direction and score>=70 else ('WATCH' if score>=55 else 'NO TRADE')
    if status=='NO TRADE': reasons.insert(0,'Trade rejected because mandatory confirmations are incomplete.')
    return {'status':status,'score':score,'entry':entry if direction else None,'stop':stop,'targets':targets,'reasons':reasons,'blockers':blockers,'what_changes':changes}
