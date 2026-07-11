"""
MongoDB Loader & KPI Engine — Uses ONLY 3 collections:
  1. course_summary → Executive Dashboard
  2. student_success_analytics → Intervention Dashboard
  3. student_success_with_survey → Diagnostic Dashboard
"""
import pandas as pd
from pymongo import MongoClient

MONGO_URI = "mongodb+srv://biuser:bi7890@cluster0.sf6hgbj.mongodb.net/?appName=Cluster0"
DB_NAME = "student_analytics"

COLLECTIONS = {
    'course_summary':       'course_summary',
    'student_success':      'student_success_analytics',
    'student_survey':       'student_success_with_survey',
}


def load_from_mongodb():
    """Load the 3 required collections from MongoDB Atlas."""
    print("⏳ Connecting to MongoDB Atlas...")
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=10000)
        client.admin.command('ping')
        print("✅ Connected!")
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return None

    db = client[DB_NAME]
    available = db.list_collection_names()
    print(f"   Database: '{DB_NAME}' | Available: {available}")

    data = {}
    for key, name in COLLECTIONS.items():
        if name not in available:
            print(f"   ⚠️ '{name}' not found")
            continue
        count = db[name].estimated_document_count()
        print(f"   Loading '{name}' ({count:,} docs) → {key}")
        # Directly pass the cursor to pd.DataFrame to save memory (avoids creating a massive list of dicts)
        df = pd.DataFrame(db[name].find({}, {'_id': 0}))
        
        if len(df) > 0:
            # Memory Optimization: Downcast numeric types and use categories for strings
            for col in df.columns:
                if df[col].dtype == 'object':
                    # Convert string objects to category if cardinality is low
                    if df[col].nunique() < len(df) * 0.5:
                        df[col] = df[col].astype('category')
                elif pd.api.types.is_numeric_dtype(df[col]):
                    # Downcast numeric types (e.g. float64 -> float32, int64 -> int32)
                    if pd.api.types.is_integer_dtype(df[col]):
                        df[col] = pd.to_numeric(df[col], downcast='integer')
                    else:
                        df[col] = pd.to_numeric(df[col], downcast='float')
            
            data[key] = df
            print(f"     ✅ {len(data[key]):,} rows | Cols: {list(data[key].columns)}")
    client.close()

    if not data:
        print("❌ No collections loaded.")
        return None
    print(f"\n✅ Loaded {len(data)} collections.")
    return data


def _col(df, candidates):
    """Find first matching column name."""
    for c in candidates:
        if c in df.columns: return c
    return None


def _num(df, col):
    """Safe numeric conversion."""
    if col and col in df.columns:
        return pd.to_numeric(df[col], errors='coerce').fillna(0)
    return pd.Series([0]*len(df))


# ==================== EXECUTIVE KPIs (course_summary) ====================
def compute_executive_kpis(data):
    cs = data.get('course_summary', pd.DataFrame())
    if len(cs) == 0:
        return dict(total_courses=0, pass_rate=0, withdrawal_rate=0, avg_score=0,
                    risk_density=0, avg_engagement=0, health_index=0)

    total_courses = len(cs)
    pr = _num(cs, 'pass_rate').mean()
    wr = _num(cs, 'withdrawal_rate').mean()
    avg_score = _num(cs, 'average_score').mean()

    total_s = _num(cs, 'total_students').sum()
    total_hr = _num(cs, 'high_risk_students').sum()
    risk_density = round((total_hr / total_s * 100), 1) if total_s > 0 else 0

    ac = _col(cs, ['average_clicks', 'average_active_days'])
    avg_eng = _num(cs, ac).mean() if ac else 0

    health = round(pr - wr, 1)

    return dict(total_courses=total_courses, pass_rate=round(pr, 1), withdrawal_rate=round(wr, 1),
                avg_score=round(avg_score, 1), risk_density=risk_density,
                avg_engagement=round(avg_eng, 0), health_index=health)


# ==================== INTERVENTION KPIs (student_success_analytics) ====================
def compute_intervention_kpis(data):
    ss = data.get('student_success', pd.DataFrame())
    if len(ss) == 0:
        return dict(high_risk=0, medium_risk=0, low_risk=0, avg_engagement=0,
                    avg_attendance=0, predicted_wd=0, immediate=0)

    rc = _col(ss, ['risk_level'])
    high = med = low = 0
    if rc:
        vc = ss[rc].value_counts()
        high = int(vc.get('High Risk', vc.get('High', 0)))
        med = int(vc.get('Medium Risk', vc.get('Medium', 0)))
        low = int(vc.get('Low Risk', vc.get('Low', 0)))

    ec = _col(ss, ['total_clicks', 'average_clicks', 'engagement_score'])
    avg_eng = round(_num(ss, ec).mean(), 0) if ec else 0

    ac = _col(ss, ['active_days', 'total_active_days', 'attendance'])
    avg_att = round(_num(ss, ac).mean(), 0) if ac else 0

    return dict(high_risk=high, medium_risk=med, low_risk=low,
                avg_engagement=avg_eng, avg_attendance=avg_att,
                predicted_wd=high, immediate=high)


# ==================== DIAGNOSTIC KPIs (student_success_with_survey) ====================
def compute_diagnostic_kpis(data):
    sv = data.get('student_survey', pd.DataFrame())
    if len(sv) == 0:
        return dict(avg_stress=0, avg_wellbeing=0, avg_lms=0, avg_satisfaction=0,
                    high_concern=0, avg_performance=0)

    avg_stress = round(_num(sv, 'stress_level').mean(), 1) if 'stress_level' in sv.columns else 0
    avg_lms = round(_num(sv, 'lms_usefulness').mean(), 1) if 'lms_usefulness' in sv.columns else 0

    sc = _col(sv, ['student_satisfaction_score', 'teaching_satisfaction'])
    avg_sat = round(_num(sv, sc).mean(), 1) if sc else 0

    high_concern = 0
    avg_wellbeing = 0
    if 'wellbeing_concern_level' in sv.columns:
        high_concern = int(sv['wellbeing_concern_level'].str.lower().str.contains('high', na=False).sum())
        cmap = {'low concern':4,'low':4,'moderate concern':3,'moderate':3,'medium':3,'high concern':1,'high':1}
        avg_wellbeing = round(sv['wellbeing_concern_level'].str.lower().map(cmap).fillna(3).mean(), 1)

    pc = _col(sv, ['average_score', 'score'])
    avg_perf = round(_num(sv, pc).mean(), 1) if pc else 0

    return dict(avg_stress=avg_stress, avg_wellbeing=avg_wellbeing, avg_lms=avg_lms,
                avg_satisfaction=avg_sat, high_concern=high_concern, avg_performance=avg_perf)


# ==================== DATA QUALITY ====================
def compute_data_quality(data):
    total_rows = sum(len(df) for df in data.values())
    total_dupes = sum(df.duplicated().sum() for df in data.values())
    total_missing = sum(df.isnull().sum().sum() for df in data.values())
    total_cells = sum(df.size for df in data.values())
    miss_pct = round(total_missing / total_cells * 100, 2) if total_cells > 0 else 0
    dup_pct = round(total_dupes / total_rows * 100, 2) if total_rows > 0 else 0
    trust = round(max(0, 100 - miss_pct - dup_pct), 1)
    tables = []
    for key, df in data.items():
        tables.append({'table': key, 'rows': len(df), 'columns': len(df.columns),
                       'missing_pct': round(df.isnull().sum().sum() / df.size * 100, 2) if df.size > 0 else 0,
                       'duplicates': int(df.duplicated().sum())})
    return dict(trust_score=trust, missing_pct=miss_pct, duplicate_pct=dup_pct, tables=tables)


# ==================== SHARED FILTER ====================
def filter_by(df, module='All', presentation='All'):
    """Apply module/presentation filters to any DataFrame that has those columns."""
    if len(df) == 0: return df
    if module != 'All' and 'code_module' in df.columns:
        df = df[df['code_module'] == module]
    if presentation != 'All' and 'code_presentation' in df.columns:
        df = df[df['code_presentation'] == presentation]
    return df


def get_at_risk_table(data, module='All', pres='All', risk_filter='All', search=''):
    """Build At-Risk Watchlist from student_success_analytics."""
    ss = data.get('student_success', pd.DataFrame())
    if len(ss) == 0: return pd.DataFrame()
    tbl = filter_by(ss.copy(), module, pres)
    if 'risk_level' in tbl.columns and risk_filter != 'All':
        tbl = tbl[tbl['risk_level'] == risk_filter]
    if search and 'id_student' in tbl.columns:
        tbl = tbl[tbl['id_student'].astype(str).str.contains(str(search), na=False)]
    cols = [c for c in ['id_student','code_module','risk_level','average_score',
                        'total_clicks','active_days','engagement_level','final_result'] if c in tbl.columns]
    return tbl[cols].head(200) if cols else pd.DataFrame()
