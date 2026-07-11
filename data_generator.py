"""
MongoDB Loader & KPI Engine — Uses ONLY 2 collections:
  1. course_summary → Executive Dashboard
  2. student_success_analytics → Intervention Dashboard
"""
import pandas as pd
from pymongo import MongoClient

MONGO_URI = "mongodb+srv://biuser:bi7890@cluster0.sf6hgbj.mongodb.net/?appName=Cluster0"
DB_NAME = "student_analytics"

COLLECTIONS = {
    'course_summary':  'course_summary',
    'student_success': 'student_success_analytics',
}


def load_from_mongodb():
    """Load the 2 required collections from MongoDB Atlas."""
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
        docs = list(db[name].find({}, {'_id': 0}))
        if docs:
            data[key] = pd.DataFrame(docs)
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
        if c in df.columns:
            return c
    return None


def _num(df, col):
    """Safe numeric conversion."""
    if col and col in df.columns:
        return pd.to_numeric(df[col], errors='coerce').fillna(0)
    return pd.Series([0] * len(df))


# ==================== EXECUTIVE KPIs (course_summary) ====================
def compute_executive_kpis(data):
    """KPIs: Total Courses, Avg Pass Rate, Avg Withdrawal Rate,
    Total High-Risk Students, Avg LMS Clicks per Student."""
    cs = data.get('course_summary', pd.DataFrame())
    if len(cs) == 0:
        return dict(total_courses=0, avg_pass_rate=0, avg_withdrawal_rate=0,
                    total_high_risk=0, avg_lms_clicks=0)

    total_courses = len(cs)
    avg_pass = round(_num(cs, 'pass_rate').mean(), 1)
    avg_wd = round(_num(cs, 'withdrawal_rate').mean(), 1)
    total_hr = int(_num(cs, 'high_risk_students').sum())

    ac = _col(cs, ['average_clicks', 'avg_clicks', 'average_active_days'])
    avg_clicks = round(_num(cs, ac).mean(), 1) if ac else 0

    return dict(total_courses=total_courses, avg_pass_rate=avg_pass,
                avg_withdrawal_rate=avg_wd, total_high_risk=total_hr,
                avg_lms_clicks=avg_clicks)


# ==================== INTERVENTION KPIs (student_success_analytics) ====================
def compute_intervention_kpis(data):
    """KPIs: Total Students, High-Risk Students, Silent Strugglers,
    Average Student Score, Average LMS Clicks."""
    ss = data.get('student_success', pd.DataFrame())
    if len(ss) == 0:
        return dict(total_students=0, high_risk=0, silent_strugglers=0,
                    avg_score=0, avg_clicks=0)

    total = len(ss)

    # High-Risk count
    rc = _col(ss, ['risk_level'])
    high_risk = 0
    if rc:
        vc = ss[rc].value_counts()
        high_risk = int(vc.get('High Risk', vc.get('High', 0)))

    # Silent Strugglers: engagement_level = Low AND 40 <= average_score < 70
    sc = _col(ss, ['average_score', 'score'])
    ec = _col(ss, ['engagement_level'])
    silent = 0
    if sc and ec:
        scores = pd.to_numeric(ss[sc], errors='coerce')
        mask = (ss[ec].str.strip().str.lower() == 'low') & (scores >= 40) & (scores < 70)
        silent = int(mask.sum())

    # Avg Score
    avg_score = round(pd.to_numeric(ss[sc], errors='coerce').mean(), 1) if sc else 0

    # Avg Clicks
    cc = _col(ss, ['total_clicks', 'sum_click', 'average_clicks'])
    avg_clicks = round(pd.to_numeric(ss[cc], errors='coerce').mean(), 0) if cc else 0

    return dict(total_students=total, high_risk=high_risk,
                silent_strugglers=silent, avg_score=avg_score,
                avg_clicks=int(avg_clicks))


# ==================== SHARED FILTER ====================
def filter_by(df, module='All', presentation='All'):
    """Apply module/presentation filters to any DataFrame."""
    if len(df) == 0:
        return df
    if module != 'All' and 'code_module' in df.columns:
        df = df[df['code_module'] == module]
    if presentation != 'All' and 'code_presentation' in df.columns:
        df = df[df['code_presentation'] == presentation]
    return df


def get_high_risk_table(ss):
    """Build High-Risk Student Watchlist.
    Columns: Student ID, Code Module, Region, Average Score, Total LMS Clicks."""
    if len(ss) == 0:
        return pd.DataFrame()
    rc = _col(ss, ['risk_level'])
    if not rc:
        return pd.DataFrame()
    hr = ss[ss[rc].isin(['High Risk', 'High'])].copy()
    # Standardise column names
    rename = {}
    if 'id_student' in hr.columns and 'student_id' not in hr.columns:
        rename['id_student'] = 'student_id'
    if 'sum_click' in hr.columns and 'total_clicks' not in hr.columns:
        rename['sum_click'] = 'total_clicks'
    hr.rename(columns=rename, inplace=True)
    cols = [c for c in ['student_id', 'code_module', 'region',
                        'average_score', 'total_clicks'] if c in hr.columns]
    return hr[cols].head(200) if cols else pd.DataFrame()


def get_silent_struggler_table(ss):
    """Build Silent Struggler Watchlist.
    Conditions: engagement_level = Low, 40 <= average_score < 70.
    Columns: Student ID, Code Module, Average Score, Total LMS Clicks."""
    if len(ss) == 0:
        return pd.DataFrame()
    sc = _col(ss, ['average_score', 'score'])
    ec = _col(ss, ['engagement_level'])
    if not sc or not ec:
        return pd.DataFrame()
    src = ss.copy()
    src[sc] = pd.to_numeric(src[sc], errors='coerce')
    mask = (src[ec].str.strip().str.lower() == 'low') & (src[sc] >= 40) & (src[sc] < 70)
    sil = src[mask].copy()
    # Standardise column names
    rename = {}
    if 'id_student' in sil.columns and 'student_id' not in sil.columns:
        rename['id_student'] = 'student_id'
    if 'sum_click' in sil.columns and 'total_clicks' not in sil.columns:
        rename['sum_click'] = 'total_clicks'
    sil.rename(columns=rename, inplace=True)
    cols = [c for c in ['student_id', 'code_module',
                        'average_score', 'total_clicks'] if c in sil.columns]
    return sil[cols].head(200) if cols else pd.DataFrame()
