"""
Charts for 2-Tab BI Dashboard.
  Executive  → course_summary        (3 charts)
  Intervention → student_success_analytics (2 charts)
"""
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import copy

# ── Base chart layout (dark theme) ──
_LAYOUT = {
    'paper_bgcolor': 'rgba(0,0,0,0)',
    'plot_bgcolor': 'rgba(0,0,0,0)',
    'font': {'family': 'Inter, sans-serif', 'color': '#F1F5F9', 'size': 12},
    'margin': {'l': 50, 'r': 30, 't': 40, 'b': 50},
    'hoverlabel': {
        'bgcolor': '#1E293B', 'font_size': 13, 'font_color': '#fff',
        'bordercolor': 'rgba(255,255,255,0.1)'
    },
    'legend': {
        'orientation': 'h', 'yanchor': 'bottom', 'y': -0.25,
        'xanchor': 'center', 'x': 0.5,
        'font': {'size': 11, 'color': '#CBD5E1'}
    },
    'xaxis': {'gridcolor': 'rgba(100,116,139,0.15)',
              'zerolinecolor': 'rgba(100,116,139,0.15)'},
    'yaxis': {'gridcolor': 'rgba(100,116,139,0.15)',
              'zerolinecolor': 'rgba(100,116,139,0.15)'},
}

_GC = 'rgba(100,116,139,0.15)'


def _gl():
    """Get a fresh copy of the base layout."""
    return copy.deepcopy(_LAYOUT)


def _empty(msg):
    """Return an empty figure with a centred message."""
    fig = go.Figure()
    layout = _gl()
    layout.update(
        height=300,
        annotations=[dict(
            text=msg, x=0.5, y=0.5, xref='paper', yref='paper',
            showarrow=False, font=dict(size=14, color='#94A3B8')
        )]
    )
    fig.update_layout(**layout)
    return fig


def _fc(df, candidates):
    """Find first matching column in DataFrame."""
    for c in candidates:
        if c in df.columns:
            return c
    return None


# ══════════════════════════════════════════════════════════════
# EXECUTIVE CHARTS  (course_summary)
# ══════════════════════════════════════════════════════════════

def exec_course_health(cs):
    """Chart 1 — Course Health Analysis (Scatter Plot).
    X: Withdrawal Rate, Y: Pass Rate, Size: Total Students, Color: Code Module.
    Hover: Code Module, Code Presentation, Pass Rate, Withdrawal Rate, Total Students."""
    if len(cs) == 0 or 'pass_rate' not in cs.columns:
        return _empty("No course data available")

    fig = px.scatter(
        cs,
        x='withdrawal_rate',
        y='pass_rate',
        size='total_students',
        color='code_module',
        hover_name='code_module',
        hover_data={
            'code_presentation': True,
            'pass_rate': ':.1f',
            'withdrawal_rate': ':.1f',
            'total_students': True,
            'code_module': False,
        },
        labels={
            'withdrawal_rate': 'Withdrawal Rate (%)',
            'pass_rate': 'Pass Rate (%)',
            'total_students': 'Total Students',
            'code_module': 'Module',
        },
        color_discrete_sequence=px.colors.qualitative.Set2,
        size_max=50,
    )
    fig.update_traces(marker=dict(
        line=dict(width=1, color='rgba(255,255,255,0.25)'),
        opacity=0.85,
    ))
    layout = _gl()
    layout.update(
        height=450,
        xaxis=dict(title='Withdrawal Rate (%)', gridcolor=_GC),
        yaxis=dict(title='Pass Rate (%)', gridcolor=_GC),
    )
    fig.update_layout(**layout)
    return fig


def exec_resource_efficiency(cs):
    """Chart 2 — Resource Efficiency Analysis (Bar Chart).
    X: Course Identifier, Y: Avg LMS Clicks per Student, Color: Pass Rate."""
    ac = _fc(cs, ['average_clicks', 'avg_clicks', 'average_active_days'])
    if len(cs) == 0 or not ac:
        return _empty("No engagement data available")

    src = cs.copy()
    src['course_id'] = src['code_module'] + ' — ' + src['code_presentation']
    src = src.sort_values(ac, ascending=False)

    fig = px.bar(
        src,
        x='course_id',
        y=ac,
        color='pass_rate',
        color_continuous_scale='Viridis',
        labels={
            'course_id': 'Course (Module — Presentation)',
            ac: 'Avg LMS Clicks per Student',
            'pass_rate': 'Pass Rate (%)',
        },
    )
    fig.update_traces(marker_line_width=0)
    layout = _gl()
    layout.update(
        height=420,
        xaxis_tickangle=-45,
        coloraxis_colorbar=dict(
            title='Pass %', len=0.6, thickness=14,
            tickfont=dict(color='#94A3B8'),
            title_font=dict(color='#94A3B8'),
        ),
    )
    fig.update_layout(**layout)
    return fig


def exec_risk_density(cs):
    """Chart 3 — High-Risk Student Density (Bar Chart).
    X: Course Identifier, Y: Number of High-Risk Students."""
    if len(cs) == 0 or 'high_risk_students' not in cs.columns:
        return _empty("No risk data available")

    src = cs.copy()
    src['course_id'] = src['code_module'] + ' — ' + src['code_presentation']
    src = src.sort_values('high_risk_students', ascending=False)

    fig = px.bar(
        src,
        x='course_id',
        y='high_risk_students',
        color='high_risk_students',
        color_continuous_scale=[[0, '#F59E0B'], [0.5, '#EF4444'], [1, '#DC2626']],
        labels={
            'course_id': 'Course (Module — Presentation)',
            'high_risk_students': 'High-Risk Students',
        },
    )
    fig.update_traces(
        marker_line_width=0,
        text=src['high_risk_students'].astype(int),
        textposition='outside',
        textfont=dict(color='#94A3B8', size=11),
    )
    layout = _gl()
    layout.update(
        height=420,
        xaxis_tickangle=-45,
        coloraxis_colorbar=dict(
            title='Count', len=0.6, thickness=14,
            tickfont=dict(color='#94A3B8'),
            title_font=dict(color='#94A3B8'),
        ),
    )
    fig.update_layout(**layout)
    return fig


# ══════════════════════════════════════════════════════════════
# INTERVENTION CHARTS  (student_success_analytics)
# ══════════════════════════════════════════════════════════════

def intv_high_risk_by_module(ss):
    """Chart 1 — High-Risk Students by Module (Bar Chart).
    X: Code Module, Y: Number of High-Risk Students."""
    if len(ss) == 0:
        return _empty("No student data available")

    rc = _fc(ss, ['risk_level'])
    if not rc:
        return _empty("No risk_level column found")

    hr = ss[ss[rc].isin(['High Risk', 'High'])]
    if len(hr) == 0:
        return _empty("No high-risk students found")

    counts = hr.groupby('code_module').size().reset_index(name='count')
    counts = counts.sort_values('count', ascending=False)

    fig = go.Figure(go.Bar(
        x=counts['code_module'],
        y=counts['count'],
        marker=dict(
            color=counts['count'],
            colorscale=[[0, '#F59E0B'], [0.5, '#EF4444'], [1, '#DC2626']],
            showscale=True,
            colorbar=dict(
                title='Count', len=0.6, thickness=14,
                tickfont=dict(color='#94A3B8'),
                title_font=dict(color='#94A3B8'),
            ),
        ),
        text=counts['count'],
        textposition='outside',
        textfont=dict(color='#94A3B8', size=12),
        hovertemplate='<b>%{x}</b><br>High-Risk Students: %{y:,}<extra></extra>',
    ))
    layout = _gl()
    layout.update(
        height=420,
        xaxis=dict(title='Code Module', gridcolor=_GC),
        yaxis=dict(title='Number of High-Risk Students', gridcolor=_GC),
    )
    fig.update_layout(**layout)
    return fig


def intv_engage_vs_perf(ss):
    """Chart 2 — Engagement vs Performance Analysis (Scatter Plot).
    X: Total LMS Clicks, Y: Average Score, Color: Risk Level,
    Marker Style: Engagement Level.
    Reference Lines: Vertical at Clicks=500, Horizontal at Score=40."""
    if len(ss) == 0:
        return _empty("No student data available")

    xc = _fc(ss, ['total_clicks', 'sum_click', 'average_clicks'])
    yc = _fc(ss, ['average_score', 'score'])
    rc = _fc(ss, ['risk_level'])
    ec = _fc(ss, ['engagement_level'])

    if not xc or not yc:
        return _empty("Missing engagement or score columns")

    src = ss.copy()
    src[xc] = pd.to_numeric(src[xc], errors='coerce')
    src[yc] = pd.to_numeric(src[yc], errors='coerce')
    src = src.dropna(subset=[xc, yc])

    if len(src) == 0:
        return _empty("No valid data points")

    sid = _fc(src, ['id_student', 'student_id'])

    color_map = {
        'High Risk': '#EF4444', 'High': '#EF4444',
        'Medium Risk': '#F59E0B', 'Medium': '#F59E0B',
        'Low Risk': '#10B981', 'Low': '#10B981',
    }
    symbol_map = {
        'High': 'circle', 'Medium': 'square', 'Low': 'diamond',
    }

    fig = go.Figure()

    # Group by risk level × engagement level for separate traces
    if rc and ec:
        for risk_val in sorted(src[rc].dropna().unique()):
            for eng_val in sorted(src[ec].dropna().unique()):
                mask = (src[rc] == risk_val) & (src[ec] == eng_val)
                sub = src[mask]
                if len(sub) == 0:
                    continue
                hover_parts = []
                for _, row in sub.iterrows():
                    parts = []
                    if sid:
                        parts.append(f"ID: {row[sid]}")
                    parts.append(f"Score: {row[yc]:.1f}")
                    parts.append(f"Clicks: {row[xc]:,.0f}")
                    if 'code_module' in sub.columns:
                        parts.append(f"Module: {row['code_module']}")
                    hover_parts.append('<br>'.join(parts))

                fig.add_trace(go.Scatter(
                    x=sub[xc], y=sub[yc],
                    mode='markers',
                    name=f"{risk_val} · {eng_val}",
                    marker=dict(
                        size=7,
                        color=color_map.get(risk_val, '#8B5CF6'),
                        symbol=symbol_map.get(eng_val, 'circle'),
                        opacity=0.7,
                        line=dict(width=0.5, color='rgba(255,255,255,0.3)'),
                    ),
                    hovertext=hover_parts,
                    hoverinfo='text',
                ))
    elif rc:
        for risk_val in src[rc].unique():
            sub = src[src[rc] == risk_val]
            fig.add_trace(go.Scatter(
                x=sub[xc], y=sub[yc],
                mode='markers', name=str(risk_val),
                marker=dict(size=7, color=color_map.get(risk_val, '#8B5CF6'), opacity=0.7),
            ))
    else:
        fig.add_trace(go.Scatter(
            x=src[xc], y=src[yc],
            mode='markers',
            marker=dict(size=7, color='#3B82F6', opacity=0.6),
        ))

    # Reference lines
    fig.add_vline(
        x=500, line_dash="dash", line_color="#64748B", line_width=1,
        annotation_text="Clicks = 500",
        annotation_font_color="#94A3B8", annotation_font_size=11,
    )
    fig.add_hline(
        y=40, line_dash="dash", line_color="#64748B", line_width=1,
        annotation_text="Score = 40",
        annotation_font_color="#94A3B8", annotation_font_size=11,
    )

    layout = _gl()
    layout.update(
        height=480,
        xaxis=dict(title='Total LMS Clicks', gridcolor=_GC),
        yaxis=dict(title='Average Score', gridcolor=_GC),
        legend=dict(y=1.08, font=dict(size=10)),
    )
    fig.update_layout(**layout)
    return fig
