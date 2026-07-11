"""
Chart builders adapted for the student_analytics data warehouse schema.
"""
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import copy

CHART_LAYOUT = {
    'paper_bgcolor': 'rgba(0,0,0,0)', 'plot_bgcolor': 'rgba(0,0,0,0)',
    'font': {'family': 'Inter, system-ui, sans-serif', 'color': '#1E293B', 'size': 12},
    'margin': {'l': 50, 'r': 20, 't': 50, 'b': 40},
    'hoverlabel': {'bgcolor': '#1E293B', 'font_size': 13, 'font_family': 'Inter, sans-serif', 'font_color': '#fff'},
    'legend': {'orientation': 'h', 'yanchor': 'bottom', 'y': -0.25, 'xanchor': 'center', 'x': 0.5, 'font': {'size': 11}},
}
DARK_CHART_LAYOUT = {
    'paper_bgcolor': 'rgba(0,0,0,0)', 'plot_bgcolor': 'rgba(0,0,0,0)',
    'font': {'family': 'Inter, system-ui, sans-serif', 'color': '#F1F5F9', 'size': 12},
    'margin': {'l': 50, 'r': 20, 't': 50, 'b': 40},
    'hoverlabel': {'bgcolor': '#334155', 'font_size': 13, 'font_family': 'Inter, sans-serif', 'font_color': '#fff'},
    'legend': {'orientation': 'h', 'yanchor': 'bottom', 'y': -0.25, 'xanchor': 'center', 'x': 0.5, 'font': {'size': 11, 'color': '#CBD5E1'}},
    'xaxis': {'gridcolor': '#334155', 'zerolinecolor': '#334155'},
    'yaxis': {'gridcolor': '#334155', 'zerolinecolor': '#334155'},
}

def _gl(dark=False):
    return copy.deepcopy(DARK_CHART_LAYOUT if dark else CHART_LAYOUT)

def _gc(dark=False):
    return '#E2E8F0' if not dark else '#334155'

def _empty(msg="No data available", dark=False):
    fig = go.Figure()
    l = _gl(dark)
    l.update(height=300, annotations=[dict(text=msg, x=0.5, y=0.5, xref='paper', yref='paper', showarrow=False, font=dict(size=14, color='#94A3B8'))])
    fig.update_layout(**l)
    return fig


def build_course_pass_rate(df_students, dark=False):
    if len(df_students) == 0 or 'code_module' not in df_students.columns or 'final_result' not in df_students.columns:
        return _empty("No student data", dark)
    result = df_students.groupby('code_module').apply(
        lambda x: (x['final_result'].isin(['Pass', 'Distinction']).sum() / len(x)) * 100, include_groups=False
    ).reset_index(name='pass_rate').sort_values('pass_rate')
    fig = go.Figure(go.Bar(
        x=result['pass_rate'], y=result['code_module'], orientation='h',
        marker=dict(color=result['pass_rate'], colorscale=[[0,'#EF4444'],[0.5,'#F59E0B'],[1,'#10B981']]),
        text=[f'{v:.1f}%' for v in result['pass_rate']], textposition='outside',
        hovertemplate='<b>%{y}</b><br>Pass Rate: %{x:.1f}%<extra></extra>'
    ))
    l = _gl(dark)
    l.update(title=None, xaxis_title='Pass Rate (%)', yaxis_title=None,
             xaxis=dict(range=[0,105], gridcolor=_gc(dark)), yaxis=dict(gridcolor=_gc(dark)), height=300)
    fig.update_layout(**l)
    return fig


def build_assessment_score_by_type(data, dark=False):
    """Uses fact_assessment_summary + dim_assessments or course_summary."""
    df_sa = data.get('student_assessments', pd.DataFrame())
    if len(df_sa) == 0:
        return _empty("No assessment data", dark)

    # fact_assessment_summary has average_score per student, not per assessment type
    # Use course_summary if available for module-level scores
    df_cs = data.get('course_summary', pd.DataFrame())
    if len(df_cs) > 0 and 'average_score' in df_cs.columns:
        avg_by_module = df_cs.groupby('code_module')['average_score'].mean().reset_index()
        avg_by_module = avg_by_module.sort_values('average_score', ascending=False)
        n = len(avg_by_module)
        colors = px.colors.sample_colorscale('Blues', np.linspace(0.4, 0.9, max(n,1)))
        fig = go.Figure(go.Bar(
            x=avg_by_module['code_module'], y=avg_by_module['average_score'],
            marker=dict(color=colors[:n]),
            text=[f"{v:.1f}" for v in avg_by_module['average_score']], textposition='outside',
            hovertemplate='<b>%{x}</b><br>Avg Score: %{y:.1f}<extra></extra>'
        ))
        l = _gl(dark)
        l.update(title=None, xaxis=dict(title='Course Module', gridcolor=_gc(dark)),
                 yaxis=dict(title='Average Score', range=[0,110], gridcolor=_gc(dark)), height=300)
        fig.update_layout(**l)
        return fig

    # Fallback: use fact_assessment_summary average_score grouped by module
    score_col = 'average_score' if 'average_score' in df_sa.columns else 'score'
    if score_col not in df_sa.columns:
        return _empty("No score column found", dark)
    df_sa = df_sa.copy()
    df_sa[score_col] = pd.to_numeric(df_sa[score_col], errors='coerce')
    if 'code_module' in df_sa.columns:
        avg = df_sa.groupby('code_module')[score_col].agg(['mean','std','count']).reset_index()
        avg.columns = ['module','avg','std','count']
        avg['std'] = avg['std'].fillna(0)
        colors_map = ['#2563EB','#10B981','#F59E0B','#EF4444','#8B5CF6','#14B8A6','#EC4899','#6366F1']
        fig = go.Figure()
        for i, (_, r) in enumerate(avg.iterrows()):
            fig.add_trace(go.Bar(x=[r['module']], y=[r['avg']], name=r['module'],
                marker=dict(color=colors_map[i % len(colors_map)]),
                text=[f"{r['avg']:.1f}"], textposition='outside',
                error_y=dict(type='data', array=[r['std']], visible=True, color='#94A3B8'),
                hovertemplate=f"<b>{r['module']}</b><br>Avg: {r['avg']:.1f}<br>Count: {r['count']:,}<extra></extra>"))
        l = _gl(dark)
        l.update(title=None, barmode='group', yaxis=dict(title='Average Score', range=[0,110], gridcolor=_gc(dark)), height=300)
        fig.update_layout(**l)
        return fig
    return _empty("No module column", dark)


def build_final_results_donut(df_students, dark=False):
    if len(df_students) == 0 or 'final_result' not in df_students.columns:
        return _empty("No result data", dark)
    counts = df_students['final_result'].value_counts().reset_index()
    counts.columns = ['result','count']
    color_map = {'Distinction':'#2563EB','Pass':'#10B981','Fail':'#EF4444','Withdrawn':'#F59E0B'}
    fig = go.Figure(go.Pie(
        labels=counts['result'], values=counts['count'], hole=0.6,
        marker=dict(colors=[color_map.get(r,'#8B5CF6') for r in counts['result']],
                    line=dict(color='#fff' if not dark else '#1E293B', width=3)),
        textinfo='percent+label',
        hovertemplate='<b>%{label}</b><br>Count: %{value:,}<br>%{percent}<extra></extra>'
    ))
    total = counts['count'].sum()
    l = _gl(dark)
    l.update(title=None, height=300, showlegend=False,
             annotations=[dict(text=f'<b>{total:,}</b><br>Students', x=0.5, y=0.5, font_size=16,
                               showarrow=False, font=dict(color='#1E293B' if not dark else '#F1F5F9'))])
    fig.update_layout(**l)
    return fig


def build_gender_pie(df_students, dark=False):
    if len(df_students) == 0 or 'gender' not in df_students.columns:
        return _empty("No gender data", dark)
    counts = df_students['gender'].value_counts().reset_index()
    counts.columns = ['gender','count']
    labels = counts['gender'].map({'M':'Male','F':'Female'}).fillna(counts['gender'])
    fig = go.Figure(go.Pie(
        labels=labels, values=counts['count'],
        marker=dict(colors=['#2563EB','#EC4899','#8B5CF6','#14B8A6'][:len(counts)],
                    line=dict(color='#fff' if not dark else '#1E293B', width=3)),
        textinfo='percent+label',
        hovertemplate='<b>%{label}</b><br>Count: %{value:,}<br>%{percent}<extra></extra>'
    ))
    l = _gl(dark)
    l.update(title=None, height=300, showlegend=False)
    fig.update_layout(**l)
    return fig


def build_age_band_bar(df_students, dark=False):
    col = 'age_band' if 'age_band' in df_students.columns else ('age_group' if 'age_group' in df_students.columns else None)
    if len(df_students) == 0 or col is None:
        return _empty("No age data", dark)
    counts = df_students[col].value_counts().reset_index()
    counts.columns = ['age','count']
    order = {'0-35':0, '35-55':1, '55<=':2}
    counts['sort'] = counts['age'].map(order)
    counts = counts.sort_values('sort')
    bar_colors = ['#2563EB','#8B5CF6','#14B8A6','#F59E0B','#EC4899'][:len(counts)]
    fig = go.Figure(go.Bar(
        x=counts['age'], y=counts['count'], marker=dict(color=bar_colors),
        text=counts['count'].apply(lambda x: f'{x:,}'), textposition='outside',
        hovertemplate='<b>%{x}</b><br>Count: %{y:,}<extra></extra>'
    ))
    l = _gl(dark)
    l.update(title=None, height=300, xaxis=dict(title='Age Band', gridcolor=_gc(dark)),
             yaxis=dict(title='Number of Students', gridcolor=_gc(dark)))
    fig.update_layout(**l)
    return fig


def build_education_bar(df_students, dark=False):
    if len(df_students) == 0 or 'highest_education' not in df_students.columns:
        return _empty("No education data", dark)
    counts = df_students['highest_education'].value_counts().reset_index()
    counts.columns = ['education','count']
    counts = counts.sort_values('count')
    n = len(counts)
    colors = px.colors.sample_colorscale('Blues', np.linspace(0.3, 0.9, max(n,1)))
    fig = go.Figure(go.Bar(
        x=counts['count'], y=counts['education'], orientation='h',
        marker=dict(color=colors[:n]),
        text=counts['count'].apply(lambda x: f'{x:,}'), textposition='outside',
        hovertemplate='<b>%{y}</b><br>Count: %{x:,}<extra></extra>'
    ))
    l = _gl(dark)
    l.update(title=None, height=300, xaxis=dict(title='Number of Students', gridcolor=_gc(dark)),
             yaxis=dict(gridcolor=_gc(dark)))
    fig.update_layout(**l)
    return fig


def build_engagement_scatter(data, df_students_filtered, dark=False):
    """Scatter: engagement vs score. Uses fact_assessment_summary + fact_lms_engagement_summary."""
    df_sa = data.get('student_assessments', pd.DataFrame())
    df_vle = data.get('student_vle', pd.DataFrame())
    if len(df_sa) == 0 or len(df_vle) == 0:
        return _empty("No engagement/assessment data", dark)

    student_ids = df_students_filtered['id_student'].unique() if 'id_student' in df_students_filtered.columns else []
    if len(student_ids) == 0:
        return _empty("No students selected", dark)

    # Get scores
    score_col = 'average_score' if 'average_score' in df_sa.columns else 'score'
    if score_col not in df_sa.columns:
        return _empty("No score column", dark)
    sa = df_sa[df_sa['id_student'].isin(student_ids)].copy() if 'id_student' in df_sa.columns else df_sa.copy()
    sa[score_col] = pd.to_numeric(sa[score_col], errors='coerce')

    # Get clicks
    click_col = None
    for c in ['total_clicks', 'sum_click', 'total_click', 'average_clicks']:
        if c in df_vle.columns:
            click_col = c
            break
    if click_col is None:
        return _empty("No click column in VLE data", dark)

    vle = df_vle[df_vle['id_student'].isin(student_ids)].copy() if 'id_student' in df_vle.columns else df_vle.copy()
    vle[click_col] = pd.to_numeric(vle[click_col], errors='coerce')

    # Merge
    scores = sa.groupby('id_student')[score_col].mean().reset_index(name='avg_score')
    clicks = vle.groupby('id_student')[click_col].sum().reset_index(name='total_clicks')
    merged = clicks.merge(scores, on='id_student', how='inner')
    merged = merged.merge(df_students_filtered[['id_student','final_result']].drop_duplicates(), on='id_student', how='left')
    merged = merged.dropna(subset=['total_clicks','avg_score'])

    if len(merged) == 0:
        return _empty("No matched data", dark)

    color_map = {'Distinction':'#2563EB','Pass':'#10B981','Fail':'#EF4444','Withdrawn':'#F59E0B'}
    fig = go.Figure()
    for result in ['Distinction','Pass','Fail','Withdrawn']:
        sub = merged[merged['final_result'] == result]
        if len(sub) == 0:
            continue
        fig.add_trace(go.Scatter(
            x=sub['total_clicks'], y=sub['avg_score'], mode='markers', name=result,
            marker=dict(size=8, color=color_map.get(result,'#8B5CF6'), opacity=0.6,
                       line=dict(width=1, color='#fff' if not dark else '#1E293B')),
            hovertemplate=f'<b>{result}</b><br>Clicks: %{{x:,}}<br>Avg Score: %{{y:.1f}}<extra></extra>'
        ))
    l = _gl(dark)
    l.update(title=None, height=380,
             xaxis=dict(title='Total VLE Clicks', gridcolor=_gc(dark)),
             yaxis=dict(title='Average Score', gridcolor=_gc(dark)),
             legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='center', x=0.5))
    fig.update_layout(**l)
    return fig


def build_daily_activity(data, student_ids, dark=False):
    """Line chart: daily activity. Adapts to available columns."""
    df_vle = data.get('student_vle', pd.DataFrame())
    if len(df_vle) == 0:
        return _empty("No VLE activity data", dark)

    vle = df_vle.copy()
    if 'id_student' in vle.columns and len(student_ids) > 0:
        vle = vle[vle['id_student'].isin(student_ids)]

    # Try to find date and click columns
    date_col = None
    for c in ['date', 'day', 'study_day']:
        if c in vle.columns:
            date_col = c
            break
    click_col = None
    for c in ['sum_click', 'total_clicks', 'average_clicks', 'total_click']:
        if c in vle.columns:
            click_col = c
            break

    if date_col is None or click_col is None:
        # If no date column, show engagement distribution instead
        if click_col and 'code_module' in vle.columns:
            agg = vle.groupby('code_module')[click_col].mean().reset_index()
            agg[click_col] = pd.to_numeric(agg[click_col], errors='coerce')
            fig = go.Figure(go.Bar(
                x=agg['code_module'], y=agg[click_col],
                marker=dict(color='#2563EB'),
                text=[f"{v:.0f}" for v in agg[click_col]], textposition='outside',
                hovertemplate='<b>%{x}</b><br>Avg Clicks: %{y:.0f}<extra></extra>'
            ))
            l = _gl(dark)
            l.update(title=None, height=320, xaxis=dict(title='Module', gridcolor=_gc(dark)),
                     yaxis=dict(title='Average Clicks', gridcolor=_gc(dark)))
            fig.update_layout(**l)
            return fig
        return _empty("No date/click columns in VLE data", dark)

    vle[date_col] = pd.to_numeric(vle[date_col], errors='coerce')
    vle[click_col] = pd.to_numeric(vle[click_col], errors='coerce')
    vle = vle.dropna(subset=[date_col, click_col])

    daily = vle.groupby(date_col)[click_col].mean().reset_index().sort_values(date_col)
    daily = daily[(daily[date_col] >= -10) & (daily[date_col] <= 300)]

    if len(daily) == 0:
        return _empty("No daily data in range", dark)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=daily[date_col], y=daily[click_col], mode='lines', name='Average Clicks',
        line=dict(color='#2563EB', width=2.5, shape='spline'),
        fill='tozeroy', fillcolor='rgba(37,99,235,0.08)',
        hovertemplate='Day %{x}<br>Avg Clicks: %{y:.1f}<extra></extra>'
    ))
    if len(daily) > 7:
        daily['rolling'] = daily[click_col].rolling(7, min_periods=1).mean()
        fig.add_trace(go.Scatter(
            x=daily[date_col], y=daily['rolling'], mode='lines', name='7-Day Average',
            line=dict(color='#F59E0B', width=2, dash='dot'),
            hovertemplate='Day %{x}<br>7-Day Avg: %{y:.1f}<extra></extra>'
        ))
    l = _gl(dark)
    l.update(title=None, height=320, xaxis=dict(title='Study Day', gridcolor=_gc(dark)),
             yaxis=dict(title='Average Clicks', gridcolor=_gc(dark)),
             legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='center', x=0.5))
    fig.update_layout(**l)
    return fig


def build_top_resources(data, student_ids, dark=False):
    """Top 10 resources. Adapts to available VLE columns."""
    df_vle = data.get('student_vle', pd.DataFrame())
    if len(df_vle) == 0:
        return _empty("No VLE data", dark)

    vle = df_vle.copy()
    if 'id_student' in vle.columns and len(student_ids) > 0:
        vle = vle[vle['id_student'].isin(student_ids)]

    # Try id_site + activity_type approach
    click_col = None
    for c in ['sum_click', 'total_clicks', 'total_click', 'average_clicks']:
        if c in vle.columns:
            click_col = c
            break
    if click_col is None:
        return _empty("No click column", dark)

    vle[click_col] = pd.to_numeric(vle[click_col], errors='coerce')

    # Try grouping by activity_type or id_site
    group_col = None
    for c in ['activity_type', 'id_site', 'resource_type']:
        if c in vle.columns:
            group_col = c
            break

    if group_col is None and 'code_module' in vle.columns:
        group_col = 'code_module'

    if group_col is None:
        return _empty("No grouping column for resources", dark)

    resource_clicks = vle.groupby(group_col)[click_col].sum().reset_index(name='total')
    top10 = resource_clicks.nlargest(10, 'total').sort_values('total')

    n = len(top10)
    colors = px.colors.sample_colorscale('Viridis', np.linspace(0.2, 0.9, max(n,1)))
    fig = go.Figure(go.Bar(
        x=top10['total'], y=top10[group_col].astype(str), orientation='h',
        marker=dict(color=colors[:n]),
        text=top10['total'].apply(lambda x: f'{x:,.0f}'), textposition='outside',
        hovertemplate='<b>%{y}</b><br>Total Clicks: %{x:,.0f}<extra></extra>'
    ))
    l = _gl(dark)
    l.update(title=None, height=380, xaxis=dict(title='Total Clicks', gridcolor=_gc(dark)),
             yaxis=dict(gridcolor=_gc(dark)), margin=dict(l=140))
    fig.update_layout(**l)
    return fig


def compute_summary(data):
    """Compute performance summary for the right panel."""
    result = {
        'best_course': 'N/A', 'best_course_rate': 0,
        'worst_course': 'N/A', 'worst_course_rate': 0,
        'high_engage': 'N/A', 'high_engage_val': 0,
        'low_engage': 'N/A', 'low_engage_val': 0,
        'at_risk': 0, 'overall_pass': 0,
    }

    # Use course_summary if available (pre-aggregated)
    df_cs = data.get('course_summary', pd.DataFrame())
    df_students = data.get('students', pd.DataFrame())

    if len(df_cs) > 0 and 'pass_rate' in df_cs.columns:
        best = df_cs.loc[df_cs['pass_rate'].idxmax()]
        worst = df_cs.loc[df_cs['pass_rate'].idxmin()]
        result['best_course'] = best['code_module']
        result['best_course_rate'] = round(best['pass_rate'], 1)
        result['worst_course'] = worst['code_module']
        result['worst_course_rate'] = round(worst['pass_rate'], 1)

        if 'average_clicks' in df_cs.columns:
            hi = df_cs.loc[df_cs['average_clicks'].idxmax()]
            lo = df_cs.loc[df_cs['average_clicks'].idxmin()]
            result['high_engage'] = hi['code_module']
            result['high_engage_val'] = int(hi['average_clicks'])
            result['low_engage'] = lo['code_module']
            result['low_engage_val'] = int(lo['average_clicks'])
    elif len(df_students) > 0 and 'final_result' in df_students.columns and 'code_module' in df_students.columns:
        cp = df_students.groupby('code_module').apply(
            lambda x: (x['final_result'].isin(['Pass','Distinction']).sum()/len(x))*100, include_groups=False)
        if len(cp) > 0:
            result['best_course'] = cp.idxmax()
            result['best_course_rate'] = round(cp.max(), 1)
            result['worst_course'] = cp.idxmin()
            result['worst_course_rate'] = round(cp.min(), 1)

    if len(df_students) > 0 and 'final_result' in df_students.columns:
        at_risk = df_students[df_students['final_result'].isin(['Fail','Withdrawn'])]
        result['at_risk'] = at_risk['id_student'].nunique() if 'id_student' in at_risk.columns else len(at_risk)
        result['overall_pass'] = round(
            (df_students['final_result'].isin(['Pass','Distinction']).sum() / len(df_students)) * 100, 1)

    return result
