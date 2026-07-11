"""
Student Performance BI Dashboard — 2 Tabs: Executive & Intervention.
Executive  → course_summary          (3 charts)
Intervention → student_success_analytics (2 charts + 2 data tables)
"""
import dash
from dash import dcc, html, dash_table, Input, Output, State
import pandas as pd
from datetime import datetime

from data_generator import (
    load_from_mongodb, compute_executive_kpis, compute_intervention_kpis,
    filter_by, get_high_risk_table, get_silent_struggler_table,
)
from charts import (
    exec_course_health, exec_resource_efficiency, exec_risk_density,
    intv_high_risk_by_module, intv_engage_vs_perf,
)

# ═══════════════════════════════════════════════════════════
# DATA LOADING
# ═══════════════════════════════════════════════════════════
print("=" * 60 + "\n  Student Performance BI Dashboard\n" + "=" * 60)
DATA = load_from_mongodb()
if DATA is None:
    DATA = {}
for k in ['course_summary', 'student_success']:
    DATA.setdefault(k, pd.DataFrame())

EK = compute_executive_kpis(DATA)
IK = compute_intervention_kpis(DATA)
print("✅ Ready!")

# ═══════════════════════════════════════════════════════════
# DASH APP
# ═══════════════════════════════════════════════════════════
app = dash.Dash(
    __name__,
    title='Student Performance BI',
    suppress_callback_exceptions=True,
    meta_tags=[{'name': 'viewport', 'content': 'width=device-width, initial-scale=1.0'}],
)
server = app.server

# Colour tokens
CL = {
    'b': '#2563EB', 'g': '#10B981', 'o': '#F59E0B',
    'p': '#8B5CF6', 'r': '#EF4444', 't': '#14B8A6',
}

# ── Filter option lists ──
cs = DATA['course_summary']
ss = DATA['student_success']
mod_o = sorted(cs['code_module'].dropna().unique().tolist()) if 'code_module' in cs.columns else []
pres_o = sorted(cs['code_presentation'].dropna().unique().tolist()) if 'code_presentation' in cs.columns else []
risk_o = sorted(ss['risk_level'].dropna().unique().tolist()) if 'risk_level' in ss.columns else []
eng_o = sorted(ss['engagement_level'].dropna().unique().tolist()) if 'engagement_level' in ss.columns else []
region_o = sorted(ss['region'].dropna().unique().tolist()) if 'region' in ss.columns else []


# ═══════════════════════════════════════════════════════════
# HELPER COMPONENTS
# ═══════════════════════════════════════════════════════════
def kpi_card(icon, label, value, color):
    """Single KPI card with gradient accent bar."""
    return html.Div([
        html.Div(style={
            'position': 'absolute', 'top': 0, 'left': 0, 'width': '100%', 'height': '4px',
            'background': f'linear-gradient(90deg, {color}, {color}88)',
            'borderRadius': '16px 16px 0 0',
        }),
        html.Div(icon, className='kpi-icon',
                 style={'background': f'{color}15', 'color': color}),
        html.Div(str(value), className='kpi-value', style={'color': color}),
        html.Div(label, className='kpi-label'),
    ], className='kpi-card')


def chart_card(title, subtitle, fig):
    """Wrap a Plotly figure in a styled card."""
    return html.Div([
        html.Div(title, className='chart-title'),
        html.Div(subtitle, className='chart-subtitle'),
        dcc.Graph(figure=fig, config={'displayModeBar': True, 'displaylogo': False}),
    ], className='chart-card')


def filter_dropdown(label, did, opts, icon='🔽'):
    """Dropdown inside a filter group."""
    option_list = [{'label': 'All', 'value': 'All'}] + \
                  [{'label': o, 'value': o} for o in opts]
    return html.Div([
        html.Div([html.Span(icon + ' '), html.Span(label)], className='filter-label'),
        dcc.Dropdown(
            id=did, options=option_list, value='All',
            clearable=False, style={'fontSize': '13px'},
        ),
    ], className='filter-group')


def summary_item(label, value, sub='', icon='📊', color='#2563EB'):
    """Right-panel summary row."""
    children = [
        html.Div([html.Span(icon + ' '), html.Span(label)], className='summary-label'),
        html.Div(str(value), className='summary-value', style={'color': color}),
    ]
    if sub:
        children.append(html.Div(sub, className='summary-sub'))
    return html.Div(children, className='summary-item')


# DataTable shared styles (dark theme)
TBL_STYLE_HEADER = {
    'backgroundColor': '#1E293B', 'color': '#94A3B8',
    'fontWeight': '700', 'fontSize': '11px',
    'textTransform': 'uppercase', 'letterSpacing': '0.5px',
    'borderBottom': '2px solid #334155',
}
TBL_STYLE_DATA = {
    'backgroundColor': '#0F172A', 'color': '#CBD5E1', 'fontSize': '13px',
}
TBL_STYLE_CELL = {'padding': '10px 14px', 'border': 'none'}
TBL_STYLE_COND = [{'if': {'row_index': 'odd'}, 'backgroundColor': '#1E293B'}]


# ═══════════════════════════════════════════════════════════
# LAYOUT
# ═══════════════════════════════════════════════════════════
app.layout = html.Div([
    dcc.Store(id='dk', data=False),
    dcc.Interval(id='clk', interval=1000, n_intervals=0),
    dcc.Download(id='dl'),

    html.Div([
        # ── HEADER ──
        html.Div([
            html.Div([
                html.Div([html.Span('🎓', style={'fontSize': '28px'})], className='header-logo'),
                html.Div([
                    html.Div('Student Performance Analytics', className='header-title'),
                    html.Div('Business Intelligence Dashboard — OULAD', className='header-subtitle'),
                ]),
            ], className='header-left'),
            html.Div([
                html.Div([
                    html.Span(id='ht', style={'fontWeight': '600'}),
                    html.Span(id='hd'),
                ], className='header-datetime'),
                html.Div([
                    html.Div([html.Span('☀️', style={'fontSize': '12px'})], className='toggle-slider'),
                ], id='dt', className='dark-toggle', n_clicks=0),
                html.Div([html.Span('🏛️', style={'fontSize': '28px'})], className='header-logo'),
            ], className='header-right'),
        ], className='header'),

        # ── SIDEBAR ──
        html.Div([
            html.Div([html.Span('⚙️ '), html.Span('Filters')], className='sidebar-title'),
            filter_dropdown('Course Module', 'f-mod', mod_o, '📚'),
            filter_dropdown('Semester', 'f-pres', pres_o, '📅'),
            # Intervention-specific filters
            html.Div(id='intv-filters', children=[
                filter_dropdown('Risk Level', 'f-risk', risk_o, '⚠️'),
                filter_dropdown('Engagement Level', 'f-eng', eng_o, '📈'),
                filter_dropdown('Region', 'f-region', region_o, '🌍'),
            ]),
            html.Button(
                [html.Span('🔄 '), html.Span('Reset Filters')],
                id='rbtn', className='reset-btn', n_clicks=0,
            ),
        ], className='sidebar'),

        # ── MAIN CONTENT ──
        html.Div([
            dcc.Tabs(id='tabs', value='executive', className='custom-tabs', children=[
                dcc.Tab(label='📊 Executive', value='executive',
                        className='custom-tab', selected_className='custom-tab--selected'),
                dcc.Tab(label='🛡️ Intervention', value='intervention',
                        className='custom-tab', selected_className='custom-tab--selected'),
            ]),
            dcc.Loading(html.Div(id='tc'), type='default'),
        ], className='main-content'),

        # ── RIGHT PANEL ──
        html.Div(id='rp', className='right-panel'),

        # ── FOOTER ──
        html.Div([
            html.Span('Student Performance BI System — Dash & Plotly'),
            html.Span('Data: course_summary · student_success_analytics',
                      style={'fontWeight': '600'}),
        ], className='footer'),

    ], className='dashboard-container', id='dc'),
])


# ═══════════════════════════════════════════════════════════
# CALLBACKS
# ═══════════════════════════════════════════════════════════

# Clock
@app.callback(
    [Output('ht', 'children'), Output('hd', 'children')],
    Input('clk', 'n_intervals'),
)
def update_clock(_):
    now = datetime.now()
    return now.strftime('%H:%M:%S'), now.strftime('%A, %B %d, %Y')


# Dark mode toggle
@app.callback(
    [Output('dk', 'data'), Output('dt', 'className')],
    Input('dt', 'n_clicks'), State('dk', 'data'),
)
def toggle_dark(n, current):
    val = not current if n and n > 0 else current
    return val, 'dark-toggle active' if val else 'dark-toggle'


app.clientside_callback(
    "function(d){document.body.classList.toggle('dark-mode',d);return '';}",
    Output('dc', 'data-dark'), Input('dk', 'data'),
)


# Reset filters
@app.callback(
    [Output('f-mod', 'value'), Output('f-pres', 'value'),
     Output('f-risk', 'value'), Output('f-eng', 'value'),
     Output('f-region', 'value')],
    Input('rbtn', 'n_clicks'), prevent_initial_call=True,
)
def reset_filters(_):
    return 'All', 'All', 'All', 'All', 'All'


# Show/hide intervention-specific filters
@app.callback(
    Output('intv-filters', 'style'),
    Input('tabs', 'value'),
)
def filter_visibility(tab):
    return {'display': 'block'} if tab == 'intervention' else {'display': 'none'}


# ═══════════════════════════════════════════════════════════
# MAIN RENDER
# ═══════════════════════════════════════════════════════════
@app.callback(
    [Output('tc', 'children'), Output('rp', 'children')],
    [Input('tabs', 'value'),
     Input('f-mod', 'value'), Input('f-pres', 'value'),
     Input('f-risk', 'value'), Input('f-eng', 'value'),
     Input('f-region', 'value'), Input('dk', 'data')],
)
def render(tab, mod, pres, risk, eng, region, dk):
    # ── Apply filters ──
    fcs = filter_by(DATA['course_summary'].copy(), mod, pres)
    fss = filter_by(DATA['student_success'].copy(), mod, pres)

    # Intervention-specific filters
    if risk != 'All' and 'risk_level' in fss.columns:
        fss = fss[fss['risk_level'] == risk]
    if eng != 'All' and 'engagement_level' in fss.columns:
        fss = fss[fss['engagement_level'] == eng]
    if region != 'All' and 'region' in fss.columns:
        fss = fss[fss['region'] == region]

    # ── Recompute KPIs on filtered data ──
    ek = compute_executive_kpis({'course_summary': fcs})
    ik = compute_intervention_kpis({'student_success': fss})

    # ═══ RIGHT PANEL ═══
    rp = []
    if tab == 'executive':
        rp = [
            html.Div('📋 Executive Summary', className='panel-title'),
            summary_item('Total Courses', ek['total_courses'], 'Active modules', '📚', CL['p']),
            summary_item('Pass Rate', f"{ek['avg_pass_rate']}%", 'Average', '✅', CL['g']),
            summary_item('Withdrawal', f"{ek['avg_withdrawal_rate']}%", 'Average', '📉', CL['o']),
            summary_item('High-Risk', f"{ek['total_high_risk']:,}", 'Total students', '🚨', CL['r']),
            summary_item('LMS Clicks', f"{ek['avg_lms_clicks']}", 'Per student avg', '🖥️', CL['b']),
        ]
    else:
        rp = [
            html.Div('🛡️ Intervention Summary', className='panel-title'),
            summary_item('Total Students', f"{ik['total_students']:,}", 'In filtered set', '👥', CL['b']),
            summary_item('High Risk', f"{ik['high_risk']:,}", 'Immediate contact', '🚨', CL['r']),
            summary_item('Silent Strugglers', f"{ik['silent_strugglers']:,}", 'Low engagement, mid score', '⚠️', CL['o']),
            summary_item('Avg Score', f"{ik['avg_score']}", 'Student average', '📊', CL['g']),
            summary_item('Avg Clicks', f"{ik['avg_clicks']:,}", 'LMS engagement', '🖥️', CL['p']),
        ]

    # ═══ TAB CONTENT ═══
    if tab == 'executive':
        content = html.Div([
            # KPIs
            html.Div([
                kpi_card('📚', 'Total Courses', ek['total_courses'], CL['p']),
                kpi_card('✅', 'Avg Pass Rate', f"{ek['avg_pass_rate']}%", CL['g']),
                kpi_card('📉', 'Avg Withdrawal Rate', f"{ek['avg_withdrawal_rate']}%", CL['o']),
                kpi_card('🚨', 'Total High-Risk Students', f"{ek['total_high_risk']:,}", CL['r']),
                kpi_card('🖥️', 'Avg LMS Clicks/Student', f"{ek['avg_lms_clicks']}", CL['b']),
            ], className='kpi-row', style={'gridTemplateColumns': 'repeat(5, 1fr)'}),

            # Chart 1 — Course Health Analysis (full width)
            html.Div([
                chart_card(
                    '🎯 Course Health Analysis',
                    'Identify courses with low pass rates & high withdrawal rates — bubble size = total students',
                    exec_course_health(fcs),
                ),
            ], className='chart-row full'),

            # Chart 2 & 3 side by side
            html.Div([
                chart_card(
                    '💡 Resource Efficiency Analysis',
                    'Evaluate whether higher LMS engagement contributes to improved student performance',
                    exec_resource_efficiency(fcs),
                ),
                chart_card(
                    '⚠️ High-Risk Student Density',
                    'Identify courses requiring additional tutors and academic support',
                    exec_risk_density(fcs),
                ),
            ], className='chart-row two-col'),
        ])

    else:  # intervention
        # Build watchlist DataFrames
        hr_df = get_high_risk_table(fss)
        hr_data = hr_df.to_dict('records') if len(hr_df) > 0 else []
        hr_cols = [
            {'name': 'Student ID', 'id': 'student_id'},
            {'name': 'Code Module', 'id': 'code_module'},
            {'name': 'Region', 'id': 'region'},
            {'name': 'Average Score', 'id': 'average_score', 'type': 'numeric',
             'format': {'specifier': '.1f'}},
            {'name': 'Total LMS Clicks', 'id': 'total_clicks', 'type': 'numeric'},
        ]
        # Keep only columns that exist in data
        hr_cols = [c for c in hr_cols if c['id'] in hr_df.columns] if len(hr_df) > 0 else hr_cols

        ss_df = get_silent_struggler_table(fss)
        ss_data = ss_df.to_dict('records') if len(ss_df) > 0 else []
        ss_cols = [
            {'name': 'Student ID', 'id': 'student_id'},
            {'name': 'Code Module', 'id': 'code_module'},
            {'name': 'Average Score', 'id': 'average_score', 'type': 'numeric',
             'format': {'specifier': '.1f'}},
            {'name': 'Total LMS Clicks', 'id': 'total_clicks', 'type': 'numeric'},
        ]
        ss_cols = [c for c in ss_cols if c['id'] in ss_df.columns] if len(ss_df) > 0 else ss_cols

        content = html.Div([
            # KPIs
            html.Div([
                kpi_card('👥', 'Total Students', f"{ik['total_students']:,}", CL['b']),
                kpi_card('🚨', 'High-Risk Students', f"{ik['high_risk']:,}", CL['r']),
                kpi_card('⚠️', 'Silent Strugglers', f"{ik['silent_strugglers']:,}", CL['o']),
                kpi_card('📊', 'Average Score', f"{ik['avg_score']}", CL['g']),
                kpi_card('🖥️', 'Average LMS Clicks', f"{ik['avg_clicks']:,}", CL['p']),
            ], className='kpi-row', style={'gridTemplateColumns': 'repeat(5, 1fr)'}),

            # Chart 1 & 2 side by side
            html.Div([
                chart_card(
                    '🚨 High-Risk Students by Module',
                    'Identify modules with the highest concentration of high-risk students',
                    intv_high_risk_by_module(fss),
                ),
                chart_card(
                    '📊 Engagement vs Performance Analysis',
                    'Total LMS Clicks vs Average Score — reference lines at Clicks=500 and Score=40',
                    intv_engage_vs_perf(fss),
                ),
            ], className='chart-row two-col'),

            # Table 1 — High-Risk Student Watchlist
            html.Div([
                html.Div([
                    html.Div([
                        html.Div('🚨 High-Risk Student Watchlist', className='chart-title',
                                 style={'color': '#EF4444'}),
                        html.Div(
                            'Students requiring immediate intervention — searchable, sortable, filterable, exportable',
                            className='chart-subtitle',
                        ),
                    ], style={'flex': '1'}),
                ], style={'display': 'flex', 'justifyContent': 'space-between',
                          'alignItems': 'flex-start', 'marginBottom': '12px'}),
                dash_table.DataTable(
                    data=hr_data, columns=hr_cols,
                    page_size=10,
                    sort_action='native',
                    filter_action='native',
                    export_format='csv',
                    style_table={'overflowX': 'auto'},
                    style_header=TBL_STYLE_HEADER,
                    style_data=TBL_STYLE_DATA,
                    style_cell=TBL_STYLE_CELL,
                    style_data_conditional=TBL_STYLE_COND,
                ),
            ], className='chart-card', style={'gridColumn': '1 / -1'}),

            # Table 2 — Silent Struggler Watchlist
            html.Div([
                html.Div([
                    html.Div([
                        html.Div('⚠️ Silent Struggler Watchlist', className='chart-title',
                                 style={'color': '#F59E0B'}),
                        html.Div(
                            'Low engagement (Engagement = Low) with mid-range scores (40 ≤ Score < 70) — '
                            'early intervention targets',
                            className='chart-subtitle',
                        ),
                    ], style={'flex': '1'}),
                ], style={'display': 'flex', 'justifyContent': 'space-between',
                          'alignItems': 'flex-start', 'marginBottom': '12px'}),
                dash_table.DataTable(
                    data=ss_data, columns=ss_cols,
                    page_size=10,
                    sort_action='native',
                    filter_action='native',
                    export_format='csv',
                    style_table={'overflowX': 'auto'},
                    style_header=TBL_STYLE_HEADER,
                    style_data=TBL_STYLE_DATA,
                    style_cell=TBL_STYLE_CELL,
                    style_data_conditional=TBL_STYLE_COND,
                ),
            ], className='chart-card', style={'gridColumn': '1 / -1'}),
        ])

    return content, rp


# ═══════════════════════════════════════════════════════════
# RUN
# ═══════════════════════════════════════════════════════════
if __name__ == '__main__':
    print("\n🚀 http://127.0.0.1:8050\n")
    app.run(debug=True, port=8050)
