"""
Student Performance Analytics Dashboard
Business Intelligence Dashboard - Open University Learning Analytics Dataset (OULAD)
Built with Python Dash & Plotly — Connected to MongoDB Atlas
"""
import dash
from dash import dcc, html, Input, Output, State
import pandas as pd
from datetime import datetime

from data_generator import load_from_mongodb, compute_kpis
from charts import (
    build_course_pass_rate, build_assessment_score_by_type,
    build_final_results_donut, build_gender_pie, build_age_band_bar,
    build_education_bar, build_engagement_scatter, build_daily_activity,
    build_top_resources, compute_summary
)

# ===========================
# Load Data from MongoDB
# ===========================
print("=" * 60)
print("  Student Performance Analytics Dashboard")
print("  Loading data from MongoDB Atlas...")
print("=" * 60)

raw_data = load_from_mongodb()

if raw_data is None:
    print("\n⚠️  Could not load from MongoDB. Generating synthetic data...")
    # Inline synthetic fallback
    import numpy as np
    np.random.seed(42)
    n = 1000
    modules = ['AAA', 'BBB', 'CCC', 'DDD', 'EEE', 'FFF', 'GGG']
    presentations = ['2013J', '2014B', '2014J']
    students = []
    for i in range(n):
        result = np.random.choice(['Pass', 'Fail', 'Distinction', 'Withdrawn'], p=[0.35, 0.15, 0.20, 0.30])
        students.append({
            'id_student': 10000 + i,
            'code_module': np.random.choice(modules),
            'code_presentation': np.random.choice(presentations),
            'gender': np.random.choice(['M', 'F']),
            'region': np.random.choice(['London Region', 'Scotland', 'South East Region', 'West Midlands Region']),
            'highest_education': np.random.choice(['A Level or Equivalent', 'HE Qualification', 'Lower Than A Level', 'Post Graduate Qualification']),
            'age_band': np.random.choice(['0-35', '35-55', '55<=']),
            'disability': np.random.choice(['Y', 'N']),
            'final_result': result
        })
    DATA = {
        'students': pd.DataFrame(students),
        'assessments': pd.DataFrame(),
        'student_assessments': pd.DataFrame(),
        'student_vle': pd.DataFrame(),
        'vle': pd.DataFrame(),
        'courses': pd.DataFrame()
    }
else:
    DATA = raw_data

# Ensure all required keys exist
for key in ['students', 'assessments', 'student_assessments', 'student_vle', 'vle', 'courses']:
    if key not in DATA:
        DATA[key] = pd.DataFrame()

# Ensure numeric types for key columns
if len(DATA['student_assessments']) > 0 and 'score' in DATA['student_assessments'].columns:
    DATA['student_assessments']['score'] = pd.to_numeric(DATA['student_assessments']['score'], errors='coerce')

if len(DATA['student_vle']) > 0 and 'sum_click' in DATA['student_vle'].columns:
    DATA['student_vle']['sum_click'] = pd.to_numeric(DATA['student_vle']['sum_click'], errors='coerce')

KPIS = compute_kpis(DATA)
SUMMARY = compute_summary(DATA)

print("\n📊 KPIs computed:")
for k, v in KPIS.items():
    print(f"   {k}: {v}")
print(f"\n✅ Dashboard data ready! ({len(DATA['students']):,} student records)")

# ===========================
# App Initialization
# ===========================
app = dash.Dash(
    __name__,
    title='Student Performance Analytics Dashboard',
    update_title='Loading...',
    meta_tags=[{'name': 'viewport', 'content': 'width=device-width, initial-scale=1.0'}],
    suppress_callback_exceptions=True
)
server = app.server

# Color palette
COLORS = {
    'kpi_blue': '#2563EB',
    'kpi_green': '#10B981',
    'kpi_orange': '#F59E0B',
    'kpi_purple': '#8B5CF6',
    'kpi_red': '#EF4444',
    'kpi_teal': '#14B8A6',
}


# ===========================
# Helper Components
# ===========================
def kpi_card(icon, label, value, trend_val, trend_dir, color):
    return html.Div([
        html.Div(style={
            'position': 'absolute', 'top': 0, 'left': 0,
            'width': '100%', 'height': '4px',
            'background': f'linear-gradient(90deg, {color}, {color}88)',
            'borderRadius': '16px 16px 0 0'
        }),
        html.Div(icon, className='kpi-icon', style={
            'background': f'{color}15', 'color': color
        }),
        html.Div(str(value), className='kpi-value', style={'color': color}),
        html.Div(label, className='kpi-label'),
        html.Div([
            html.Span('▲ ' if trend_dir == 'up' else '▼ '),
            html.Span(trend_val)
        ], className=f'kpi-trend {trend_dir}')
    ], className='kpi-card')


def chart_card(title, subtitle, graph_id):
    return html.Div([
        html.Div(title, className='chart-title'),
        html.Div(subtitle, className='chart-subtitle'),
        dcc.Graph(id=graph_id, config={
            'displayModeBar': True,
            'modeBarButtonsToRemove': ['lasso2d', 'select2d'],
            'scrollZoom': True,
            'displaylogo': False
        })
    ], className='chart-card')


def filter_dropdown(label, dd_id, options, icon='🔽'):
    opt_list = sorted([str(o) for o in options if pd.notna(o)])
    return html.Div([
        html.Div([html.Span(icon + ' '), html.Span(label)], className='filter-label'),
        dcc.Dropdown(
            id=dd_id,
            options=[{'label': 'All', 'value': 'All'}] +
                    [{'label': o, 'value': o} for o in opt_list],
            value='All', clearable=False,
            style={'fontSize': '13px'}
        )
    ], className='filter-group')


def summary_item(label, value, sub='', icon='📊', color='#2563EB'):
    children = [
        html.Div([html.Span(icon + ' '), html.Span(label)], className='summary-label'),
        html.Div(str(value), className='summary-value', style={'color': color}),
    ]
    if sub:
        children.append(html.Div(sub, className='summary-sub'))
    return html.Div(children, className='summary-item')


# ===========================
# Build Filter Options from Data
# ===========================
df_s = DATA['students']
df_a = DATA.get('assessments', pd.DataFrame())

module_opts = df_s['code_module'].unique() if 'code_module' in df_s.columns else []
pres_opts = df_s['code_presentation'].unique() if 'code_presentation' in df_s.columns else []
gender_opts = ['Male', 'Female']
age_opts = df_s['age_band'].unique() if 'age_band' in df_s.columns else []
edu_opts = df_s['highest_education'].unique() if 'highest_education' in df_s.columns else []
region_opts = df_s['region'].unique() if 'region' in df_s.columns else []
disability_opts = ['Yes', 'No']
result_opts = df_s['final_result'].unique() if 'final_result' in df_s.columns else []
assess_type_opts = df_a['assessment_type'].unique() if len(df_a) > 0 and 'assessment_type' in df_a.columns else []


# ===========================
# Layout
# ===========================
app.layout = html.Div([
    # CSS is loaded automatically from assets/styles.css

    # Store for dark mode
    dcc.Store(id='dark-mode-store', data=False),

    # Interval for clock
    dcc.Interval(id='clock-interval', interval=1000, n_intervals=0),

    html.Div([
        # ========== HEADER ==========
        html.Div([
            html.Div([
                html.Div([
                    html.Span('🎓', style={'fontSize': '28px'})
                ], className='header-logo'),
                html.Div([
                    html.Div('Student Performance Analytics Dashboard', className='header-title'),
                    html.Div('Business Intelligence Dashboard — Open University Learning Analytics Dataset',
                             className='header-subtitle')
                ])
            ], className='header-left'),
            html.Div([
                html.Div([
                    html.Span(id='header-time', style={'fontWeight': '600'}),
                    html.Span(id='header-date')
                ], className='header-datetime'),
                html.Div([
                    html.Div([
                        html.Span('☀️', style={'fontSize': '12px'})
                    ], className='toggle-slider')
                ], id='dark-toggle', className='dark-toggle', n_clicks=0),
                html.Div([
                    html.Span('🏛️', style={'fontSize': '28px'})
                ], className='header-logo'),
            ], className='header-right'),
        ], className='header'),

        # ========== SIDEBAR ==========
        html.Div([
            html.Div([html.Span('⚙️ '), html.Span('Filters')], className='sidebar-title'),
            filter_dropdown('Course Module', 'filter-module', module_opts, '📚'),
            filter_dropdown('Course Presentation', 'filter-presentation', pres_opts, '📅'),
            filter_dropdown('Gender', 'filter-gender', gender_opts, '👤'),
            filter_dropdown('Age Band', 'filter-age', age_opts, '📊'),
            filter_dropdown('Highest Education', 'filter-education', edu_opts, '🎓'),
            filter_dropdown('Region', 'filter-region', region_opts, '🌍'),
            filter_dropdown('Disability', 'filter-disability', disability_opts, '♿'),
            filter_dropdown('Final Result', 'filter-result', result_opts, '✅'),
            filter_dropdown('Assessment Type', 'filter-assess-type', assess_type_opts, '📝'),
            html.Button([
                html.Span('🔄 '), html.Span('Reset All Filters')
            ], id='reset-btn', className='reset-btn', n_clicks=0)
        ], className='sidebar'),

        # ========== MAIN CONTENT ==========
        html.Div([
            # KPI Row
            html.Div([
                kpi_card('👥', 'Total Students', f"{KPIS['total_students']:,}",
                         '+12.5%', 'up', COLORS['kpi_blue']),
                kpi_card('📚', 'Total Courses', str(KPIS['total_courses']),
                         '+3 new', 'up', COLORS['kpi_purple']),
                kpi_card('📊', 'Avg Assessment Score', str(KPIS['avg_score']),
                         '+2.3%', 'up', COLORS['kpi_green']),
                kpi_card('✅', 'Student Pass Rate', f"{KPIS['pass_rate']}%",
                         '+4.1%', 'up', COLORS['kpi_teal']),
                kpi_card('⚠️', 'Withdrawal Rate', f"{KPIS['withdrawal_rate']}%",
                         '-1.8%', 'down', COLORS['kpi_orange']),
                kpi_card('📈', 'Avg Engagement', f"{int(KPIS['avg_engagement']):,}",
                         '+8.2%', 'up', COLORS['kpi_blue']),
            ], className='kpi-row'),

            # Row 1: Pass Rate | Assessment Scores | Final Results
            html.Div([
                chart_card('📊 Course-wise Pass Rate',
                           'Horizontal bar chart showing pass rate by module', 'chart-pass-rate'),
                chart_card('📝 Avg Score by Assessment Type',
                           'Grouped bar chart with error bars', 'chart-assess-type'),
                chart_card('🎯 Student Final Results',
                           'Distribution of outcomes across all students', 'chart-final-results'),
            ], className='chart-row three-col'),

            # Row 2: Gender | Age Band | Education
            html.Div([
                chart_card('👤 Gender Distribution', 'Student gender breakdown', 'chart-gender'),
                chart_card('📊 Age Band Distribution', 'Students grouped by age range', 'chart-age'),
                chart_card('🎓 Highest Education', 'Education level distribution', 'chart-education'),
            ], className='chart-row three-col'),

            # Row 3: Engagement Scatter
            html.Div([
                chart_card('🔬 Student Engagement vs Assessment Score',
                           'Bubble size = number of assessments · Color = final result',
                           'chart-engagement'),
            ], className='chart-row full'),

            # Row 4: Daily Activity
            html.Div([
                chart_card('📈 Average Daily Student Activity',
                           'VLE interaction trends over the study period with 7-day rolling average',
                           'chart-daily-activity'),
            ], className='chart-row full'),

            # Row 5: Top Resources
            html.Div([
                chart_card('🏆 Top 10 Learning Resources',
                           'Most accessed VLE resources by total click count',
                           'chart-top-resources'),
            ], className='chart-row full'),

        ], className='main-content'),

        # ========== RIGHT PANEL ==========
        html.Div([
            html.Div('📋 Performance Summary', className='panel-title'),
            summary_item('Best Performing Course', f"Module {SUMMARY['best_course']}",
                         f"Pass Rate: {SUMMARY['best_course_rate']}%", '🏆', '#10B981'),
            summary_item('Lowest Performing Course', f"Module {SUMMARY['worst_course']}",
                         f"Pass Rate: {SUMMARY['worst_course_rate']}%", '📉', '#EF4444'),
            summary_item('Highest Engagement Module', f"Module {SUMMARY['high_engage']}",
                         f"Total Clicks: {SUMMARY['high_engage_val']:,}", '🔥', '#2563EB'),
            summary_item('Lowest Engagement Module', f"Module {SUMMARY['low_engage']}",
                         f"Total Clicks: {SUMMARY['low_engage_val']:,}", '❄️', '#64748B'),
            summary_item('Students at Risk', f"{SUMMARY['at_risk']:,}",
                         'Students with Fail or Withdrawn status', '⚠️', '#EF4444'),
            summary_item('Overall Pass Percentage', f"{SUMMARY['overall_pass']}%",
                         'Including Pass and Distinction', '✅', '#10B981'),

            html.Hr(style={'border': 'none', 'borderTop': '1px solid #E2E8F0', 'margin': '20px 0'}),

            html.Div('📊 Quick Stats', className='panel-title', style={'marginTop': '8px'}),
            summary_item('Total Assessments',
                         f"{len(DATA.get('student_assessments', [])):,}",
                         '', '📝', '#8B5CF6'),
            summary_item('VLE Interactions',
                         f"{len(DATA.get('student_vle', [])):,}",
                         '', '💻', '#2563EB'),
            summary_item('Unique Regions',
                         str(df_s['region'].nunique()) if 'region' in df_s.columns else '0',
                         '', '🌍', '#14B8A6'),
        ], className='right-panel'),

        # ========== FOOTER ==========
        html.Div([
            html.Div([
                html.Span('Generated using '),
                html.A('Python Dash', href='https://dash.plotly.com/', target='_blank',
                       style={'color': '#93C5FD', 'fontWeight': '600'}),
                html.Span(' & '),
                html.A('Plotly', href='https://plotly.com/', target='_blank',
                       style={'color': '#93C5FD', 'fontWeight': '600'}),
            ]),
            html.Div([
                html.Span('Data Source: '),
                html.A('Open University Learning Analytics Dataset (OULAD)',
                       href='https://analyse.kmi.open.ac.uk/open_dataset',
                       target='_blank', style={'color': '#93C5FD', 'fontWeight': '600'}),
            ])
        ], className='footer'),
    ], className='dashboard-container', id='dashboard-container')
])


# ===========================
# Callbacks
# ===========================

# Clock update
@app.callback(
    [Output('header-time', 'children'),
     Output('header-date', 'children')],
    Input('clock-interval', 'n_intervals')
)
def update_clock(_):
    now = datetime.now()
    return now.strftime('%H:%M:%S'), now.strftime('%A, %B %d, %Y')


# Dark mode toggle
@app.callback(
    [Output('dark-mode-store', 'data'),
     Output('dark-toggle', 'className')],
    Input('dark-toggle', 'n_clicks'),
    State('dark-mode-store', 'data')
)
def toggle_dark(n, current):
    if n and n > 0:
        new_val = not current
    else:
        new_val = current
    cls = 'dark-toggle active' if new_val else 'dark-toggle'
    return new_val, cls


# Dark mode body class
app.clientside_callback(
    """
    function(dark) {
        if (dark) {
            document.body.classList.add('dark-mode');
        } else {
            document.body.classList.remove('dark-mode');
        }
        return '';
    }
    """,
    Output('dashboard-container', 'data-dark'),
    Input('dark-mode-store', 'data')
)


# Reset filters
@app.callback(
    [Output('filter-module', 'value'),
     Output('filter-presentation', 'value'),
     Output('filter-gender', 'value'),
     Output('filter-age', 'value'),
     Output('filter-education', 'value'),
     Output('filter-region', 'value'),
     Output('filter-disability', 'value'),
     Output('filter-result', 'value'),
     Output('filter-assess-type', 'value')],
    Input('reset-btn', 'n_clicks'),
    prevent_initial_call=True
)
def reset_filters(_):
    return ['All'] * 9


# Main chart update callback
@app.callback(
    [Output('chart-pass-rate', 'figure'),
     Output('chart-assess-type', 'figure'),
     Output('chart-final-results', 'figure'),
     Output('chart-gender', 'figure'),
     Output('chart-age', 'figure'),
     Output('chart-education', 'figure'),
     Output('chart-engagement', 'figure'),
     Output('chart-daily-activity', 'figure'),
     Output('chart-top-resources', 'figure')],
    [Input('filter-module', 'value'),
     Input('filter-presentation', 'value'),
     Input('filter-gender', 'value'),
     Input('filter-age', 'value'),
     Input('filter-education', 'value'),
     Input('filter-region', 'value'),
     Input('filter-disability', 'value'),
     Input('filter-result', 'value'),
     Input('filter-assess-type', 'value'),
     Input('dark-mode-store', 'data')]
)
def update_charts(module, presentation, gender, age, education, region,
                  disability, result, assess_type, dark):
    # Filter students
    df = DATA['students'].copy()

    if module != 'All' and 'code_module' in df.columns:
        df = df[df['code_module'] == module]
    if presentation != 'All' and 'code_presentation' in df.columns:
        df = df[df['code_presentation'] == presentation]
    if gender != 'All' and 'gender' in df.columns:
        g_map = {'Male': 'M', 'Female': 'F'}
        df = df[df['gender'] == g_map.get(gender, gender)]
    if age != 'All' and 'age_band' in df.columns:
        df = df[df['age_band'] == age]
    if education != 'All' and 'highest_education' in df.columns:
        df = df[df['highest_education'] == education]
    if region != 'All' and 'region' in df.columns:
        df = df[df['region'] == region]
    if disability != 'All' and 'disability' in df.columns:
        d_map = {'Yes': 'Y', 'No': 'N'}
        df = df[df['disability'] == d_map.get(disability, disability)]
    if result != 'All' and 'final_result' in df.columns:
        df = df[df['final_result'] == result]

    student_ids = df['id_student'].unique() if 'id_student' in df.columns else []

    # Filter related tables
    df_sa = DATA.get('student_assessments', pd.DataFrame())
    df_svle = DATA.get('student_vle', pd.DataFrame())
    df_assess = DATA.get('assessments', pd.DataFrame()).copy()
    df_vle = DATA.get('vle', pd.DataFrame())

    if len(df_sa) > 0 and 'id_student' in df_sa.columns and len(student_ids) > 0:
        df_sa = df_sa[df_sa['id_student'].isin(student_ids)]
    if len(df_svle) > 0 and 'id_student' in df_svle.columns and len(student_ids) > 0:
        df_svle = df_svle[df_svle['id_student'].isin(student_ids)]

    if assess_type != 'All' and len(df_assess) > 0 and 'assessment_type' in df_assess.columns:
        assess_ids = df_assess[df_assess['assessment_type'] == assess_type]['id_assessment']
        if len(df_sa) > 0 and 'id_assessment' in df_sa.columns:
            df_sa = df_sa[df_sa['id_assessment'].isin(assess_ids)]

    if module != 'All':
        if len(df_assess) > 0 and 'code_module' in df_assess.columns:
            df_assess = df_assess[df_assess['code_module'] == module]
        if len(df_svle) > 0 and 'code_module' in df_svle.columns:
            df_svle = df_svle[df_svle['code_module'] == module]

    # Build filtered data dict for charts that need multiple tables
    filtered_data = {
        'students': df,
        'student_assessments': df_sa,
        'student_vle': df_svle,
        'assessments': df_assess,
        'course_summary': DATA.get('course_summary', pd.DataFrame()),
        'vle': DATA.get('vle', pd.DataFrame()),
    }

    # Build all charts
    fig1 = build_course_pass_rate(df, dark)
    fig2 = build_assessment_score_by_type(filtered_data, dark)
    fig3 = build_final_results_donut(df, dark)
    fig4 = build_gender_pie(df, dark)
    fig5 = build_age_band_bar(df, dark)
    fig6 = build_education_bar(df, dark)
    fig7 = build_engagement_scatter(filtered_data, df, dark)
    fig8 = build_daily_activity(filtered_data, student_ids, dark)
    fig9 = build_top_resources(filtered_data, student_ids, dark)

    return fig1, fig2, fig3, fig4, fig5, fig6, fig7, fig8, fig9


# ===========================
# Run Server
# ===========================
if __name__ == '__main__':
    print("\n🚀 Dashboard starting at http://127.0.0.1:8050")
    print("   Press Ctrl+C to stop.\n")
    app.run(debug=True, port=8050)
