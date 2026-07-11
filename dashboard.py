"""Student Performance BI Dashboard — 3 Collections, 4 Tabs."""
import dash
from dash import dcc, html, dash_table, Input, Output, State
import pandas as pd
from datetime import datetime

from data_generator import (load_from_mongodb, compute_executive_kpis, compute_intervention_kpis,
    compute_diagnostic_kpis, compute_data_quality, filter_by, get_at_risk_table)
from charts import (exec_course_health, exec_outcome_donut, exec_resource_efficiency, exec_risk_density,
    exec_performance_trend, intv_risk_donut, intv_engage_vs_perf, intv_silent_struggler, intv_risk_by_category,
    diag_stress_vs_perf, diag_wellbeing_bar, diag_lms_friction, diag_sentiment_pie, diag_correlation,
    cross_retention_funnel, cross_success_gap)

# ===== LOAD =====
print("="*60+"\n  Student Performance BI Dashboard\n"+"="*60)
DATA = load_from_mongodb()
if DATA is None: DATA = {}
for k in ['course_summary','student_success','student_survey']:
    DATA.setdefault(k, pd.DataFrame())

EK = compute_executive_kpis(DATA)
IK = compute_intervention_kpis(DATA)
DK = compute_diagnostic_kpis(DATA)
DQ = compute_data_quality(DATA)
print(f"✅ Ready! Trust Score: {DQ['trust_score']}%")

# ===== APP =====
app = dash.Dash(__name__, title='Student Performance BI', suppress_callback_exceptions=True,
    meta_tags=[{'name':'viewport','content':'width=device-width, initial-scale=1.0'}])
server = app.server
CL = {'b':'#2563EB','g':'#10B981','o':'#F59E0B','p':'#8B5CF6','r':'#EF4444','t':'#14B8A6','pk':'#EC4899','i':'#6366F1'}

# ===== HELPERS =====
def kpi(icon, label, value, color):
    return html.Div([
        html.Div(style={'position':'absolute','top':0,'left':0,'width':'100%','height':'4px',
            'background':f'linear-gradient(90deg,{color},{color}88)','borderRadius':'16px 16px 0 0'}),
        html.Div(icon,className='kpi-icon',style={'background':f'{color}15','color':color}),
        html.Div(str(value),className='kpi-value',style={'color':color}),
        html.Div(label,className='kpi-label')
    ],className='kpi-card')

def cc(title,sub,fig):
    return html.Div([html.Div(title,className='chart-title'),html.Div(sub,className='chart-subtitle'),
        dcc.Graph(figure=fig,config={'displayModeBar':True,'displaylogo':False})],className='chart-card')

def fdd(label,did,opts,icon='🔽'):
    ol=sorted([str(o) for o in opts if pd.notna(o)])
    return html.Div([html.Div([html.Span(icon+' '),html.Span(label)],className='filter-label'),
        dcc.Dropdown(id=did,options=[{'label':'All','value':'All'}]+[{'label':o,'value':o} for o in ol],
            value='All',clearable=False,style={'fontSize':'13px'})],className='filter-group')

def si(label,value,sub='',icon='📊',color='#2563EB'):
    ch=[html.Div([html.Span(icon+' '),html.Span(label)],className='summary-label'),
        html.Div(str(value),className='summary-value',style={'color':color})]
    if sub: ch.append(html.Div(sub,className='summary-sub'))
    return html.Div(ch,className='summary-item')

# Filter options from course_summary
cs=DATA['course_summary']; ss=DATA['student_success']; sv=DATA['student_survey']
mod_o=cs['code_module'].unique() if 'code_module' in cs.columns else []
pres_o=cs['code_presentation'].unique() if 'code_presentation' in cs.columns else []
risk_o=ss['risk_level'].unique().tolist() if 'risk_level' in ss.columns else []
stress_o=sorted(sv['stress_level'].dropna().unique().tolist()) if 'stress_level' in sv.columns else []
wb_o=sv['wellbeing_concern_level'].unique().tolist() if 'wellbeing_concern_level' in sv.columns else []

# ===== LAYOUT =====
app.layout = html.Div([
    dcc.Store(id='dk',data=False), dcc.Interval(id='clk',interval=1000,n_intervals=0), dcc.Download(id='dl'),
    html.Div([
        # HEADER
        html.Div([
            html.Div([html.Div([html.Span('🎓',style={'fontSize':'28px'})],className='header-logo'),
                html.Div([html.Div('Student Performance Analytics',className='header-title'),
                    html.Div('Business Intelligence Dashboard — OULAD',className='header-subtitle')])],className='header-left'),
            html.Div([html.Div([html.Span(id='ht',style={'fontWeight':'600'}),html.Span(id='hd')],className='header-datetime'),
                html.Div([html.Div([html.Span('☀️',style={'fontSize':'12px'})],className='toggle-slider')],id='dt',className='dark-toggle',n_clicks=0),
                html.Div([html.Span('🏛️',style={'fontSize':'28px'})],className='header-logo')],className='header-right'),
        ],className='header'),

        # SIDEBAR
        html.Div([
            html.Div([html.Span('⚙️ '),html.Span('Filters')],className='sidebar-title'),
            fdd('Course Module','f-mod',mod_o,'📚'), fdd('Semester','f-pres',pres_o,'📅'),
            # Intervention-specific
            html.Div(id='intv-filters',children=[
                fdd('Risk Level','f-risk',risk_o,'⚠️'),
                html.Div([html.Div([html.Span('🔍 '),html.Span('Search Student ID')],className='filter-label'),
                    dcc.Input(id='f-search',type='text',placeholder='Enter Student ID...',debounce=True,
                        style={'width':'100%','padding':'8px','borderRadius':'8px','border':'1px solid #E2E8F0','fontSize':'13px'})
                ],className='filter-group'),
            ]),
            # Diagnostic-specific
            html.Div(id='diag-filters',children=[
                fdd('Stress Level','f-stress',stress_o,'🧠'),
                fdd('Wellbeing','f-wb',wb_o,'❤️'),
            ]),
            html.Button([html.Span('🔄 '),html.Span('Reset Filters')],id='rbtn',className='reset-btn',n_clicks=0),
        ],className='sidebar'),

        # MAIN
        html.Div([
            dcc.Tabs(id='tabs',value='executive',className='custom-tabs',children=[
                dcc.Tab(label='📊 Executive',value='executive',className='custom-tab',selected_className='custom-tab--selected'),
                dcc.Tab(label='🛡️ Intervention',value='intervention',className='custom-tab',selected_className='custom-tab--selected'),
                dcc.Tab(label='🔬 Diagnostic',value='diagnostic',className='custom-tab',selected_className='custom-tab--selected'),
                dcc.Tab(label='📈 Cross-Analysis',value='cross',className='custom-tab',selected_className='custom-tab--selected'),
            ]),
            dcc.Loading(html.Div(id='tc'),type='default')
        ],className='main-content'),

        # RIGHT PANEL
        html.Div(id='rp',className='right-panel'),

        # FOOTER
        html.Div([html.Span('Student Performance BI System — Dash & Plotly'),
            html.Span(f'Data Trust Score: {DQ["trust_score"]}%',style={'fontWeight':'600'})],className='footer'),
    ],className='dashboard-container',id='dc')
])

# ===== CALLBACKS =====
@app.callback([Output('ht','children'),Output('hd','children')],Input('clk','n_intervals'))
def _clk(_): n=datetime.now(); return n.strftime('%H:%M:%S'),n.strftime('%A, %B %d, %Y')

@app.callback([Output('dk','data'),Output('dt','className')],Input('dt','n_clicks'),State('dk','data'))
def _dk(n,c): v=not c if n and n>0 else c; return v,'dark-toggle active' if v else 'dark-toggle'

app.clientside_callback("function(d){document.body.classList.toggle('dark-mode',d);return '';}",Output('dc','data-dark'),Input('dk','data'))

@app.callback([Output('f-mod','value'),Output('f-pres','value'),Output('f-risk','value'),
    Output('f-search','value'),Output('f-stress','value'),Output('f-wb','value')],
    Input('rbtn','n_clicks'),prevent_initial_call=True)
def _rst(_): return 'All','All','All','','All','All'

# Show/hide tab-specific filters
@app.callback([Output('intv-filters','style'),Output('diag-filters','style')],Input('tabs','value'))
def _fvis(tab):
    intv={'display':'block'} if tab=='intervention' else {'display':'none'}
    diag={'display':'block'} if tab=='diagnostic' else {'display':'none'}
    return intv, diag

# ===== MAIN RENDER =====
@app.callback([Output('tc','children'),Output('rp','children')],
    [Input('tabs','value'),Input('f-mod','value'),Input('f-pres','value'),
     Input('f-risk','value'),Input('f-search','value'),
     Input('f-stress','value'),Input('f-wb','value'),Input('dk','data')])
def render(tab,mod,pres,risk,search,stress,wb,dk):
    # Filter each collection
    fcs = filter_by(DATA['course_summary'].copy(), mod, pres)
    fss = filter_by(DATA['student_success'].copy(), mod, pres)
    fsv = filter_by(DATA['student_survey'].copy(), mod, pres)

    # Extra intervention filters
    if risk!='All' and 'risk_level' in fss.columns: fss=fss[fss['risk_level']==risk]
    if search and 'id_student' in fss.columns: fss=fss[fss['id_student'].astype(str).str.contains(str(search),na=False)]

    # Extra diagnostic filters
    if stress!='All' and 'stress_level' in fsv.columns:
        fsv=fsv[fsv['stress_level'].astype(str)==str(stress)]
    if wb!='All' and 'wellbeing_concern_level' in fsv.columns:
        fsv=fsv[fsv['wellbeing_concern_level']==wb]

    # ===== RIGHT PANEL =====
    rp=[]
    if tab=='executive':
        rp=[html.Div('📋 Executive Summary',className='panel-title'),
            si('Total Courses',EK['total_courses'],'Active modules','📚',CL['p']),
            si('Pass Rate',f"{EK['pass_rate']}%",'Overall','✅',CL['g']),
            si('Withdrawal',f"{EK['withdrawal_rate']}%",'Overall','📉',CL['o']),
            si('Health Index',EK['health_index'],'Pass% − Withdrawal%','💚',CL['t']),
            si('Avg Score',f"{EK['avg_score']}%",'All courses','📊',CL['b'])]
    elif tab=='intervention':
        rp=[html.Div('🛡️ Actions Required',className='panel-title'),
            si('High Risk',f"{IK['high_risk']:,}",'Immediate contact','🚨',CL['r']),
            si('Medium Risk',f"{IK['medium_risk']:,}",'Monitor','⚠️',CL['o']),
            si('Low Risk',f"{IK['low_risk']:,}",'On track','✅',CL['g']),
            si('Avg Attendance',f"{IK['avg_attendance']}",'Active days','📅',CL['b'])]
    elif tab=='diagnostic':
        rp=[html.Div('🔬 Root Cause KPIs',className='panel-title'),
            si('Avg Stress',f"{DK['avg_stress']}/5",'Stress level','🧠',CL['o']),
            si('Satisfaction',f"{DK['avg_satisfaction']}/5",'Overall','❤️',CL['t']),
            si('LMS Rating',f"{DK['avg_lms']}/5",'Usefulness','💻',CL['b']),
            si('High Concern',f"{DK['high_concern']:,}",'Wellbeing flagged','🚩',CL['r'])]
    else:
        rp=[html.Div('📈 Data Quality',className='panel-title'),
            si('Trust Score',f"{DQ['trust_score']}%",'Data reliability','🛡️',CL['g']),
            si('Missing',f"{DQ['missing_pct']}%",'Null values','📋',CL['o']),
            si('Duplicates',f"{DQ['duplicate_pct']}%",'Duplicate rows','📋',CL['r'])]

    # ===== TAB CONTENT =====
    if tab=='executive':
        content=html.Div([
            html.Div([kpi('📚','Total Courses',EK['total_courses'],CL['p']),
                kpi('✅','Pass Rate',f"{EK['pass_rate']}%",CL['g']),
                kpi('📉','Withdrawal',f"{EK['withdrawal_rate']}%",CL['o']),
                kpi('📊','Avg Score',f"{EK['avg_score']}%",CL['b']),
                kpi('🚨','Risk Density',f"{EK['risk_density']}%",CL['r']),
                kpi('📈','Avg Engagement',f"{int(EK['avg_engagement']):,}",CL['i']),
                kpi('💚','Health Index',EK['health_index'],CL['t'])
            ],className='kpi-row',style={'gridTemplateColumns':'repeat(4,1fr)'}),
            html.Div([cc('📊 Course Performance Analysis','Pass, Fail & Withdrawal rates by module',exec_course_health(fcs,dk)),
                cc('🎯 Student Outcome Distribution','Overall academic outcomes',exec_outcome_donut(fcs,dk))],className='chart-row two-col'),
            html.Div([cc('💡 Resource Efficiency','LMS Clicks vs Pass Rate',exec_resource_efficiency(fcs,dk)),
                cc('⚠️ Risk Density by Course','High-risk student concentration',exec_risk_density(fcs,dk))],className='chart-row two-col'),
            html.Div([cc('📈 Performance Trends','Score & rate trends across semesters',exec_performance_trend(fcs,dk))],className='chart-row full'),
        ])

    elif tab=='intervention':
        ar=get_at_risk_table(DATA,mod,pres,risk,search)
        ar_d=ar.to_dict('records') if len(ar)>0 else []
        ar_c=[{'name':c.replace('_',' ').title(),'id':c} for c in ar.columns] if len(ar)>0 else []
        content=html.Div([
            html.Div([kpi('🚨','High Risk',f"{IK['high_risk']:,}",CL['r']),
                kpi('⚠️','Medium Risk',f"{IK['medium_risk']:,}",CL['o']),
                kpi('✅','Low Risk',f"{IK['low_risk']:,}",CL['g']),
                kpi('📈','Avg Engagement',f"{int(IK['avg_engagement']):,}",CL['b']),
                kpi('📅','Avg Attendance',f"{int(IK['avg_attendance'])}",CL['t']),
                kpi('📉','Predicted WD',f"{IK['predicted_wd']:,}",CL['pk']),
                kpi('🔔','Immediate',f"{IK['immediate']:,}",CL['r'])
            ],className='kpi-row',style={'gridTemplateColumns':'repeat(4,1fr)'}),
            # Watchlist
            html.Div([html.Div([html.Div([html.Div('🚨 At-Risk Student Watchlist',className='chart-title',style={'color':'#EF4444'}),
                    html.Div('Students requiring intervention — sortable, filterable, exportable',className='chart-subtitle')],
                    style={'flex':'1'}),
                html.Button([html.Span('📥 '),html.Span('Export CSV')],id='exp',className='export-btn',n_clicks=0)],
                style={'display':'flex','justifyContent':'space-between','alignItems':'flex-start','marginBottom':'12px'}),
                dash_table.DataTable(data=ar_d,columns=ar_c,page_size=12,sort_action='native',filter_action='native',
                    style_table={'overflowX':'auto'},
                    style_header={'backgroundColor':'#1E293B' if dk else '#F8FAFC','color':'#F1F5F9' if dk else '#475569',
                        'fontWeight':'700','fontSize':'11px','textTransform':'uppercase','borderBottom':'2px solid '+('#334155' if dk else '#E2E8F0')},
                    style_data={'backgroundColor':'#0F172A' if dk else '#fff','color':'#F1F5F9' if dk else '#1E293B','fontSize':'13px'},
                    style_cell={'padding':'10px 14px','border':'none'},
                    style_data_conditional=[{'if':{'row_index':'odd'},'backgroundColor':'#1E293B' if dk else '#F8FAFC'}])
            ],className='chart-card',style={'gridColumn':'1/-1'}),
            html.Div([cc('🎯 Risk Distribution','Student risk composition',intv_risk_donut(fss,dk)),
                cc('📊 Engagement vs Performance','Score by engagement level',intv_engage_vs_perf(fss,dk))],className='chart-row two-col'),
            html.Div([cc('🕵️ Silent Struggler Analysis','Low engagement + mid scores',intv_silent_struggler(fss,dk)),
                cc('📊 Risk by Category','Student count per risk level',intv_risk_by_category(fss,dk))],className='chart-row two-col'),
        ])

    elif tab=='diagnostic':
        content=html.Div([
            html.Div([kpi('🧠','Avg Stress',f"{DK['avg_stress']}/5",CL['o']),
                kpi('❤️','Wellbeing',f"{DK['avg_wellbeing']}/5",CL['t']),
                kpi('💻','LMS Usefulness',f"{DK['avg_lms']}/5",CL['b']),
                kpi('⭐','Satisfaction',f"{DK['avg_satisfaction']}/5",CL['g']),
                kpi('🚩','High Concern',f"{DK['high_concern']:,}",CL['r']),
                kpi('📊','Avg Performance',DK['avg_performance'],CL['p'])
            ],className='kpi-row',style={'gridTemplateColumns':'repeat(3,1fr)'}),
            html.Div([cc('📉 Stress vs Performance','Impact of stress on scores',diag_stress_vs_perf(fsv,dk)),
                cc('💬 Wellbeing Concern Analysis','Score by wellbeing level',diag_wellbeing_bar(fsv,dk))],className='chart-row two-col'),
            html.Div([cc('💻 LMS Friction Analysis','Platform usefulness vs usage',diag_lms_friction(fsv,dk)),
                cc('🧩 Sentiment Distribution','Overall wellbeing composition',diag_sentiment_pie(fsv,dk))],className='chart-row two-col'),
            html.Div([cc('🔗 Correlation Matrix','Success factor relationships',diag_correlation(fsv,dk))],className='chart-row full'),
        ])

    else:  # cross
        sgd=cross_success_gap(DATA)
        sg_d=sgd.to_dict('records') if len(sgd)>0 else []
        sg_c=[{'name':c.replace('_',' ').title(),'id':c} for c in sgd.columns] if len(sgd)>0 else []
        dq_d=DQ.get('tables',[])
        dq_c=[{'name':k.replace('_',' ').title(),'id':k} for k in ['table','rows','columns','missing_pct','duplicates']] if dq_d else []
        content=html.Div([
            html.Div([kpi('🛡️','Trust Score',f"{DQ['trust_score']}%",CL['g']),
                kpi('📋','Missing',f"{DQ['missing_pct']}%",CL['o']),
                kpi('📋','Duplicates',f"{DQ['duplicate_pct']}%",CL['r'])
            ],className='kpi-row',style={'gridTemplateColumns':'repeat(3,1fr)'}),
            html.Div([html.Div('🔍 Success Gap Analysis',className='chart-title'),
                html.Div('Average metrics by risk level — stress, engagement, attendance',className='chart-subtitle'),
                dash_table.DataTable(data=sg_d,columns=sg_c,page_size=10,
                    style_header={'backgroundColor':'#1E293B' if dk else '#F8FAFC','color':'#F1F5F9' if dk else '#475569','fontWeight':'700'},
                    style_data={'backgroundColor':'#0F172A' if dk else '#fff','color':'#F1F5F9' if dk else '#1E293B'},
                    style_cell={'padding':'10px 14px','border':'none'})],className='chart-card'),
            html.Div([cc('📉 Retention Funnel','Enrolled → Passed → Failed → Withdrawn',cross_retention_funnel(fcs,dk))],className='chart-row full'),
            html.Div([html.Div('🛡️ Data Quality Report',className='chart-title'),
                html.Div('Source collection audit',className='chart-subtitle'),
                dash_table.DataTable(data=dq_d,columns=dq_c,page_size=10,
                    style_header={'backgroundColor':'#1E293B' if dk else '#F8FAFC','color':'#F1F5F9' if dk else '#475569','fontWeight':'700'},
                    style_data={'backgroundColor':'#0F172A' if dk else '#fff','color':'#F1F5F9' if dk else '#1E293B'},
                    style_cell={'padding':'10px 14px','border':'none'})],className='chart-card'),
        ])

    return content, rp

# CSV Export
@app.callback(Output('dl','data'),Input('exp','n_clicks'),
    [State('f-mod','value'),State('f-pres','value'),State('f-risk','value'),State('f-search','value')],
    prevent_initial_call=True)
def export(n,mod,pres,risk,search):
    if not n: return dash.no_update
    ar=get_at_risk_table(DATA,mod,pres,risk,search)
    return dcc.send_data_frame(ar.to_csv,'at_risk_students.csv',index=False) if len(ar)>0 else dash.no_update

if __name__=='__main__':
    print("\n🚀 http://127.0.0.1:8050\n")
    app.run(debug=True, port=8050)
