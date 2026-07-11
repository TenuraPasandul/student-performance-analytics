"""
MongoDB Data Loader for the Student Performance Analytics Dashboard.
Connects to MongoDB Atlas and loads the student_analytics data warehouse.

Database: student_analytics
Collections:
  - dim_student_profile     → students (32,593 docs)
  - dim_courses             → courses (22 docs)
  - dim_assessments         → assessments dimension
  - fact_assessment_summary → student assessment facts (25,843 docs)
  - fact_lms_engagement_summary → VLE/LMS engagement facts
  - fact_student_survey_simulated → student survey data
  - course_summary          → pre-aggregated course stats (22 docs)
  - student_success_analytics → combined analytics
"""
import pandas as pd
from pymongo import MongoClient

MONGO_URI = "mongodb+srv://biuser:bi7890@cluster0.sf6hgbj.mongodb.net/?appName=Cluster0"
DB_NAME = "student_analytics"

# Explicit mapping: internal key → MongoDB collection name
COLLECTION_MAP = {
    'students':             'dim_student_profile',
    'courses':              'dim_courses',
    'assessments':          'dim_assessments',
    'student_assessments':  'fact_assessment_summary',
    'student_vle':          'fact_lms_engagement_summary',
    'student_survey':       'fact_student_survey_simulated',
    'course_summary':       'course_summary',
    'student_success':      'student_success_analytics',
    'student_success_survey': 'student_success_with_survey',
}


def load_from_mongodb():
    """Connect to MongoDB Atlas and load all collections into DataFrames."""
    print("⏳ Connecting to MongoDB Atlas...")

    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=10000)
        client.admin.command('ping')
        print("✅ Connected to MongoDB Atlas!")
    except Exception as e:
        print(f"❌ MongoDB connection failed: {e}")
        return None

    db = client[DB_NAME]
    available = db.list_collection_names()
    print(f"   Database: '{DB_NAME}'")
    print(f"   Collections: {available}")

    data = {}
    for key, coll_name in COLLECTION_MAP.items():
        if coll_name not in available:
            print(f"   ⚠️ Collection '{coll_name}' not found, skipping → {key}")
            continue

        coll = db[coll_name]
        count = coll.estimated_document_count()
        print(f"   Loading '{coll_name}' ({count:,} docs) → {key}")

        docs = list(coll.find({}, {'_id': 0}))
        if docs:
            df = pd.DataFrame(docs)
            data[key] = df
            print(f"     ✅ {len(df):,} rows | Columns: {list(df.columns)}")
        else:
            print(f"     ⚠️ Empty collection")

    client.close()

    if 'students' not in data:
        print("\n❌ Missing required collection: dim_student_profile")
        return None

    print(f"\n✅ Loaded {len(data)} collections from MongoDB!")
    return data


def compute_kpis(data):
    """Compute KPI values from the loaded data."""
    df_students = data.get('students', pd.DataFrame())
    if len(df_students) == 0:
        return {'total_students': 0, 'total_courses': 0, 'avg_score': 0,
                'pass_rate': 0, 'withdrawal_rate': 0, 'avg_engagement': 0}

    total_students = df_students['id_student'].nunique() if 'id_student' in df_students.columns else len(df_students)

    # Total courses from course_summary or dim_courses or student profiles
    if 'course_summary' in data and len(data['course_summary']) > 0:
        total_courses = len(data['course_summary'])
    elif 'courses' in data and len(data['courses']) > 0:
        total_courses = len(data['courses'])
    elif 'code_module' in df_students.columns:
        total_courses = df_students[['code_module', 'code_presentation']].drop_duplicates().shape[0]
    else:
        total_courses = 0

    # Average assessment score from fact_assessment_summary
    avg_score = 0
    df_sa = data.get('student_assessments', pd.DataFrame())
    if len(df_sa) > 0 and 'average_score' in df_sa.columns:
        avg_score = pd.to_numeric(df_sa['average_score'], errors='coerce').mean()
    elif len(df_sa) > 0 and 'score' in df_sa.columns:
        avg_score = pd.to_numeric(df_sa['score'], errors='coerce').mean()

    # Pass rate and withdrawal rate
    pass_rate = 0
    withdrawal_rate = 0
    if 'final_result' in df_students.columns:
        total = len(df_students)
        pass_rate = (df_students['final_result'].isin(['Pass', 'Distinction']).sum() / total) * 100
        withdrawal_rate = (df_students['final_result'] == 'Withdrawn').sum() / total * 100

    # Average engagement from fact_lms_engagement_summary
    avg_engagement = 0
    df_vle = data.get('student_vle', pd.DataFrame())
    if len(df_vle) > 0:
        for click_col in ['total_clicks', 'sum_click', 'total_click', 'average_clicks']:
            if click_col in df_vle.columns:
                avg_engagement = pd.to_numeric(df_vle[click_col], errors='coerce').mean()
                break

    return {
        'total_students': total_students,
        'total_courses': total_courses,
        'avg_score': round(avg_score, 1) if pd.notna(avg_score) else 0,
        'pass_rate': round(pass_rate, 1),
        'withdrawal_rate': round(withdrawal_rate, 1),
        'avg_engagement': round(avg_engagement, 0) if pd.notna(avg_engagement) else 0
    }
