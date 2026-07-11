"""Charts for 3-collection BI Dashboard."""
import plotly.graph_objects as go, pandas as pd, numpy as np, copy

_L={'paper_bgcolor':'rgba(0,0,0,0)','plot_bgcolor':'rgba(0,0,0,0)','font':{'family':'Inter,sans-serif','color':'#1E293B','size':12},'margin':{'l':50,'r':20,'t':40,'b':40},'hoverlabel':{'bgcolor':'#1E293B','font_size':13,'font_color':'#fff'},'legend':{'orientation':'h','yanchor':'bottom','y':-.25,'xanchor':'center','x':.5,'font':{'size':11}}}
_D={'paper_bgcolor':'rgba(0,0,0,0)','plot_bgcolor':'rgba(0,0,0,0)','font':{'family':'Inter,sans-serif','color':'#F1F5F9','size':12},'margin':{'l':50,'r':20,'t':40,'b':40},'hoverlabel':{'bgcolor':'#334155','font_size':13,'font_color':'#fff'},'legend':{'orientation':'h','yanchor':'bottom','y':-.25,'xanchor':'center','x':.5,'font':{'size':11,'color':'#CBD5E1'}},'xaxis':{'gridcolor':'#334155'},'yaxis':{'gridcolor':'#334155'}}
def _gl(d): return copy.deepcopy(_D if d else _L)
def _gc(d): return '#334155' if d else '#E2E8F0'
def _e(msg,d=False):
    f=go.Figure();l=_gl(d);l.update(height=300,annotations=[dict(text=msg,x=.5,y=.5,xref='paper',yref='paper',showarrow=False,font=dict(size=14,color='#94A3B8'))]);f.update_layout(**l);return f
def _fc(df,cs):
    for c in cs:
        if c in df.columns: return c
    return None

# ===== EXECUTIVE (course_summary) =====

def exec_course_health(cs, d=False):
    if len(cs)==0 or 'pass_rate' not in cs.columns: return _e("No course data",d)
    cs=cs.copy(); cs['fail_rate']=100-cs.get('pass_rate',0)-cs.get('withdrawal_rate',0); cs=cs.sort_values('pass_rate')
    fig=go.Figure()
    for col,nm,clr in [('pass_rate','Pass Rate','#10B981'),('fail_rate','Fail Rate','#EF4444'),('withdrawal_rate','Withdrawal Rate','#F59E0B')]:
        if col in cs.columns: fig.add_trace(go.Bar(y=cs['code_module'],x=cs[col],name=nm,orientation='h',marker_color=clr,hovertemplate=f'<b>%{{y}}</b><br>{nm}: %{{x:.1f}}%<extra></extra>'))
    l=_gl(d);l.update(barmode='stack',height=380,xaxis=dict(title='Percentage (%)',gridcolor=_gc(d)),yaxis=dict(gridcolor=_gc(d)));fig.update_layout(**l);return fig

def exec_outcome_donut(cs, d=False):
    if len(cs)==0: return _e("No data",d)
    p=cs['pass_count'].sum() if 'pass_count' in cs.columns else 0
    f=cs['fail_count'].sum() if 'fail_count' in cs.columns else 0
    w=cs['withdrawn_count'].sum() if 'withdrawn_count' in cs.columns else 0
    if p+f+w==0: return _e("No outcome data",d)
    fig=go.Figure(go.Pie(labels=['Passed','Failed','Withdrawn'],values=[p,f,w],hole=.6,
        marker=dict(colors=['#10B981','#EF4444','#F59E0B'],line=dict(width=2,color='#fff' if not d else '#1E293B')),textinfo='percent+label'))
    tot=p+f+w;l=_gl(d);l.update(height=300,showlegend=False,annotations=[dict(text=f'<b>{tot:,}</b><br>Students',x=.5,y=.5,font_size=15,showarrow=False,font=dict(color='#1E293B' if not d else '#F1F5F9'))]);fig.update_layout(**l);return fig

def exec_resource_efficiency(cs, d=False):
    if len(cs)==0 or 'average_clicks' not in cs.columns: return _e("No data",d)
    fig=go.Figure(go.Scatter(x=cs['average_clicks'],y=cs['pass_rate'],mode='markers+text',text=cs['code_module'],textposition='top center',
        marker=dict(size=14,color=cs['pass_rate'],colorscale='RdYlGn',showscale=True,colorbar=dict(title='Pass%',len=.6),line=dict(width=1,color='#fff')),
        hovertemplate='<b>%{text}</b><br>Clicks: %{x:.0f}<br>Pass: %{y:.1f}%<extra></extra>'))
    l=_gl(d);l.update(height=350,xaxis=dict(title='Average LMS Clicks',gridcolor=_gc(d)),yaxis=dict(title='Pass Rate (%)',gridcolor=_gc(d)));fig.update_layout(**l);return fig

def exec_risk_density(cs, d=False):
    if len(cs)==0 or 'high_risk_students' not in cs.columns: return _e("No data",d)
    cs=cs.copy();cs['density']=(cs['high_risk_students']/cs['total_students'])*100;cs=cs.sort_values('density',ascending=False)
    fig=go.Figure(go.Bar(x=cs['code_module'],y=cs['density'],marker=dict(color=cs['density'],colorscale=[[0,'#F59E0B'],[1,'#EF4444']]),
        text=[f'{v:.1f}%' for v in cs['density']],textposition='outside',customdata=cs['high_risk_students'],
        hovertemplate='<b>%{x}</b><br>Density: %{y:.1f}%<br>Count: %{customdata}<extra></extra>'))
    l=_gl(d);l.update(height=350,xaxis=dict(title='Course Module',gridcolor=_gc(d)),yaxis=dict(title='Risk Density (%)',gridcolor=_gc(d)));fig.update_layout(**l);return fig

def exec_performance_trend(cs, d=False):
    if len(cs)==0 or 'code_presentation' not in cs.columns: return _e("No trend data",d)
    agg=cs.groupby('code_presentation').agg(avg_score=('average_score','mean'),pass_rate=('pass_rate','mean'),wd=('withdrawal_rate','mean')).reset_index().sort_values('code_presentation')
    fig=go.Figure()
    for col,nm,clr in [('avg_score','Avg Score','#2563EB'),('pass_rate','Pass Rate','#10B981'),('wd','Withdrawal','#EF4444')]:
        fig.add_trace(go.Scatter(x=agg['code_presentation'],y=agg[col],mode='lines+markers',name=nm,line=dict(color=clr,width=2.5),marker=dict(size=8)))
    l=_gl(d);l.update(height=350,xaxis=dict(title='Semester',gridcolor=_gc(d)),yaxis=dict(title='%',gridcolor=_gc(d)),legend=dict(y=1.05));fig.update_layout(**l);return fig

# ===== INTERVENTION (student_success_analytics) =====

def intv_risk_donut(ss, d=False):
    if len(ss)==0: return _e("No data",d)
    rc=_fc(ss,['risk_level'])
    if not rc: return _e("No risk_level column",d)
    ct=ss[rc].value_counts().reset_index();ct.columns=['level','count']
    cm={'High Risk':'#EF4444','High':'#EF4444','Medium Risk':'#F59E0B','Medium':'#F59E0B','Low Risk':'#10B981','Low':'#10B981'}
    fig=go.Figure(go.Pie(labels=ct['level'],values=ct['count'],hole=.6,
        marker=dict(colors=[cm.get(r,'#8B5CF6') for r in ct['level']],line=dict(width=2,color='#fff' if not d else '#1E293B')),textinfo='percent+label'))
    l=_gl(d);l.update(height=300,showlegend=False);fig.update_layout(**l);return fig

def intv_engage_vs_perf(ss, d=False):
    if len(ss)==0: return _e("No data",d)
    xc=_fc(ss,['total_clicks','average_clicks','engagement_score']);yc=_fc(ss,['average_score','score'])
    if not xc or not yc: return _e("Missing columns",d)
    src=ss.copy();src[xc]=pd.to_numeric(src[xc],errors='coerce');src[yc]=pd.to_numeric(src[yc],errors='coerce');src=src.dropna(subset=[xc,yc])
    rc=_fc(src,['risk_level','final_result'])
    cm={'High Risk':'#EF4444','Medium Risk':'#F59E0B','Low Risk':'#10B981','Fail':'#EF4444','Withdrawn':'#F59E0B','Pass':'#10B981','Distinction':'#2563EB'}
    fig=go.Figure()
    if rc:
        for v in src[rc].unique():
            sub=src[src[rc]==v];fig.add_trace(go.Scatter(x=sub[xc],y=sub[yc],mode='markers',name=str(v),marker=dict(size=6,color=cm.get(v,'#8B5CF6'),opacity=.6)))
    else:
        fig.add_trace(go.Scatter(x=src[xc],y=src[yc],mode='markers',marker=dict(size=6,color='#2563EB',opacity=.6)))
    l=_gl(d);l.update(height=370,xaxis=dict(title='Engagement',gridcolor=_gc(d)),yaxis=dict(title='Average Score',gridcolor=_gc(d)),legend=dict(y=1.05));fig.update_layout(**l);return fig

def intv_silent_struggler(ss, d=False):
    if len(ss)==0: return _e("No data",d)
    xc=_fc(ss,['total_clicks','average_clicks']);yc=_fc(ss,['average_score','score']);sc=_fc(ss,['active_days','total_active_days','attendance'])
    if not xc or not yc: return _e("Missing columns",d)
    src=ss.copy();src[xc]=pd.to_numeric(src[xc],errors='coerce');src[yc]=pd.to_numeric(src[yc],errors='coerce')
    if sc: src[sc]=pd.to_numeric(src[sc],errors='coerce')
    src=src.dropna(subset=[xc,yc])
    q1=src[xc].quantile(.25);lo=src[yc].quantile(.3);hi=src[yc].quantile(.7)
    src['cat']=np.where((src[xc]<=q1)&(src[yc].between(lo,hi)),'Silent Struggler','Other')
    fig=go.Figure()
    oth=src[src['cat']=='Other'];sil=src[src['cat']=='Silent Struggler']
    if len(oth)>0: fig.add_trace(go.Scatter(x=oth[xc],y=oth[yc],mode='markers',name='Other',marker=dict(size=5,color='#94A3B8',opacity=.3)))
    if len(sil)>0:
        sz=sil[sc].clip(5,30) if sc and sc in sil.columns else 10
        fig.add_trace(go.Scatter(x=sil[xc],y=sil[yc],mode='markers',name='Silent Strugglers',marker=dict(size=sz,color='#F59E0B',opacity=.8,line=dict(width=1,color='#fff'))))
    l=_gl(d);l.update(height=380,xaxis=dict(title='Engagement (Clicks)',gridcolor=_gc(d)),yaxis=dict(title='Average Score',gridcolor=_gc(d)),legend=dict(y=1.05));fig.update_layout(**l);return fig

def intv_risk_by_category(ss, d=False):
    if len(ss)==0: return _e("No data",d)
    rc=_fc(ss,['risk_level'])
    if not rc: return _e("No risk column",d)
    ct=ss[rc].value_counts().reset_index();ct.columns=['level','count']
    cm={'High Risk':'#EF4444','High':'#EF4444','Medium Risk':'#F59E0B','Medium':'#F59E0B','Low Risk':'#10B981','Low':'#10B981'}
    fig=go.Figure(go.Bar(x=ct['level'],y=ct['count'],marker=dict(color=[cm.get(v,'#8B5CF6') for v in ct['level']]),
        text=ct['count'].apply(lambda x:f'{x:,}'),textposition='outside'))
    l=_gl(d);l.update(height=350,xaxis=dict(title='Risk Level',gridcolor=_gc(d)),yaxis=dict(title='Student Count',gridcolor=_gc(d)));fig.update_layout(**l);return fig

# ===== DIAGNOSTIC (student_success_with_survey) =====

def diag_stress_vs_perf(sv, d=False):
    if len(sv)==0 or 'stress_level' not in sv.columns: return _e("No survey data",d)
    sc=_fc(sv,['average_score','score','student_satisfaction_score'])
    if not sc: return _e("No score column",d)
    src=sv.copy();src['stress_level']=pd.to_numeric(src['stress_level'],errors='coerce');src[sc]=pd.to_numeric(src[sc],errors='coerce')
    agg=src.groupby('stress_level')[sc].mean().reset_index().sort_values('stress_level')
    fig=go.Figure(go.Scatter(x=agg['stress_level'],y=agg[sc],mode='lines+markers',line=dict(color='#EF4444',width=3),marker=dict(size=10),
        hovertemplate='Stress: %{x}<br>Avg Score: %{y:.1f}<extra></extra>'))
    l=_gl(d);l.update(height=350,xaxis=dict(title='Stress Level',gridcolor=_gc(d)),yaxis=dict(title='Average Score',gridcolor=_gc(d)));fig.update_layout(**l);return fig

def diag_wellbeing_bar(sv, d=False):
    if len(sv)==0 or 'wellbeing_concern_level' not in sv.columns: return _e("No data",d)
    sc=_fc(sv,['average_score','student_satisfaction_score','score'])
    if not sc: return _e("No score col",d)
    src=sv.copy();src[sc]=pd.to_numeric(src[sc],errors='coerce')
    agg=src.groupby('wellbeing_concern_level')[sc].mean().reset_index()
    cm={'Low Concern':'#10B981','Low':'#10B981','Moderate Concern':'#F59E0B','Medium':'#F59E0B','High Concern':'#EF4444','High':'#EF4444'}
    fig=go.Figure(go.Bar(x=agg['wellbeing_concern_level'],y=agg[sc],marker=dict(color=[cm.get(v,'#8B5CF6') for v in agg['wellbeing_concern_level']]),
        text=[f'{v:.1f}' for v in agg[sc]],textposition='outside'))
    l=_gl(d);l.update(height=350,xaxis=dict(title='Wellbeing Concern Level',gridcolor=_gc(d)),yaxis=dict(title=f'Avg Score',gridcolor=_gc(d)));fig.update_layout(**l);return fig

def diag_lms_friction(sv, d=False):
    if len(sv)==0 or 'lms_usefulness' not in sv.columns: return _e("No LMS data",d)
    cc=_fc(sv,['total_clicks','average_clicks']);sc=_fc(sv,['average_score','score'])
    if not cc: return _e("No clicks column",d)
    src=sv.copy();src['lms_usefulness']=pd.to_numeric(src['lms_usefulness'],errors='coerce');src[cc]=pd.to_numeric(src[cc],errors='coerce')
    sz=src[sc].clip(3,20) if sc and sc in src.columns else 8
    fig=go.Figure(go.Scatter(x=src['lms_usefulness'],y=src[cc],mode='markers',
        marker=dict(size=sz,color='#3B82F6',opacity=.4,line=dict(width=.5,color='#fff')),
        hovertemplate='LMS Rating: %{x}<br>Clicks: %{y:,}<extra></extra>'))
    l=_gl(d);l.update(height=350,xaxis=dict(title='LMS Usefulness',gridcolor=_gc(d)),yaxis=dict(title='Total Clicks',gridcolor=_gc(d)));fig.update_layout(**l);return fig

def diag_sentiment_pie(sv, d=False):
    if len(sv)==0 or 'wellbeing_concern_level' not in sv.columns: return _e("No data",d)
    ct=sv['wellbeing_concern_level'].value_counts().reset_index();ct.columns=['level','count']
    cm={'Low Concern':'#10B981','Low':'#10B981','Moderate Concern':'#F59E0B','Medium':'#F59E0B','High Concern':'#EF4444','High':'#EF4444'}
    fig=go.Figure(go.Pie(labels=ct['level'],values=ct['count'],
        marker=dict(colors=[cm.get(v,'#8B5CF6') for v in ct['level']],line=dict(width=2,color='#fff' if not d else '#1E293B')),textinfo='percent+label'))
    l=_gl(d);l.update(height=300,showlegend=False);fig.update_layout(**l);return fig

def diag_correlation(sv, d=False):
    if len(sv)==0: return _e("No data",d)
    cands=['stress_level','lms_usefulness','total_clicks','active_days','average_score','student_satisfaction_score','teaching_satisfaction','assessment_fairness']
    cols=[c for c in cands if c in sv.columns]
    if len(cols)<2: return _e("Not enough columns",d)
    num=sv[cols].apply(pd.to_numeric,errors='coerce').dropna()
    if len(num)<5: return _e("Not enough data",d)
    corr=num.corr();labels=[c.replace('_',' ').title() for c in corr.columns]
    fig=go.Figure(go.Heatmap(z=corr.values,x=labels,y=labels,colorscale='RdBu_r',zmid=0,zmin=-1,zmax=1,
        text=np.round(corr.values,2),texttemplate='%{text}',hovertemplate='%{x} vs %{y}<br>r = %{z:.2f}<extra></extra>'))
    l=_gl(d);l.update(height=420,margin=dict(l=130,b=110));fig.update_layout(**l);return fig

# ===== CROSS-DASHBOARD =====

def cross_retention_funnel(cs, d=False):
    if len(cs)==0: return _e("No data",d)
    p=cs['pass_count'].sum() if 'pass_count' in cs.columns else 0
    f=cs['fail_count'].sum() if 'fail_count' in cs.columns else 0
    w=cs['withdrawn_count'].sum() if 'withdrawn_count' in cs.columns else 0
    tot=p+f+w
    if tot==0: return _e("No outcome data",d)
    fig=go.Figure(go.Funnel(y=['Enrolled','Passed','Failed','Withdrawn'],x=[tot,p,f,w],
        marker=dict(color=['#2563EB','#10B981','#EF4444','#F59E0B']),
        textinfo='value+percent initial'))
    l=_gl(d);l.update(height=350);fig.update_layout(**l);return fig

def cross_success_gap(data):
    ss=data.get('student_success',pd.DataFrame())
    if len(ss)==0 or 'risk_level' not in ss.columns: return pd.DataFrame()
    agg_cols={}
    for c in ['average_score','total_clicks','active_days']:
        if c in ss.columns: agg_cols[c]='mean'
    if not agg_cols: return pd.DataFrame()
    result=ss.groupby('risk_level').agg(**{k:(k,'mean') for k in agg_cols}).reset_index()
    # try to add stress from survey
    sv=data.get('student_survey',pd.DataFrame())
    if len(sv)>0 and 'stress_level' in sv.columns and 'id_student' in sv.columns and 'id_student' in ss.columns:
        merged=pd.merge(ss[['id_student','risk_level']],sv[['id_student','stress_level']],on='id_student',how='inner')
        sa=merged.groupby('risk_level')['stress_level'].mean().reset_index()
        result=pd.merge(result,sa,on='risk_level',how='left')
    for c in result.select_dtypes(include='number').columns: result[c]=result[c].round(1)
    return result
