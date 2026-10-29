import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os

# --- Page Configuration ---
st.set_page_config(
    page_title="College Academic & Attendance Analytics",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Custom Styling ---
st.markdown("""
<style>
    .metric-card {
        background-color: #ffffff;
        border-radius: 8px;
        padding: 14px 18px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.12), 0 1px 2px rgba(0,0,0,0.24);
        margin-bottom: 10px;
    }
    .metric-value {
        font-size: 26px;
        font-weight: 700;
        color: #1f2937;
    }
    .metric-label {
        font-size: 13px;
        color: #6b7280;
        text-transform: uppercase;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# --- Data Loading Function ---
@st.cache_data
def load_and_prepare_data(file_path):
    xls = pd.ExcelFile(file_path)
    students = pd.read_excel(xls, 'Students')
    attendance = pd.read_excel(xls, 'Attendance')
    sessions = pd.read_excel(xls, 'Class_Sessions')
    exams = pd.read_excel(xls, 'Examinations')
    faculty = pd.read_excel(xls, 'Faculty')
    marks = pd.read_excel(xls, 'Student_Marks')
    subjects = pd.read_excel(xls, 'Subjects')
    calendar = pd.read_excel(xls, 'Academic_Calendar')

    # Trim string values
    for df in [students, attendance, sessions, exams, faculty, marks, subjects, calendar]:
        for col in df.select_dtypes(include='object').columns:
            df[col] = df[col].astype(str).str.strip()

    # Drop duplicate 'division' from sessions before merging to avoid collision
    sessions_clean = sessions.drop(columns=['division'], errors='ignore')

    # Join Attendance
    att_merged = attendance.merge(sessions_clean, on='session_id', how='left')
    att_merged = att_merged.merge(
        students[['student_id', 'student_name', 'department', 'track_code', 'division', 'semester']],
        on='student_id', how='left'
    )
    att_merged = att_merged.merge(subjects[['subject_id', 'subject_name']], on='subject_id', how='left')
    att_eligible = att_merged[att_merged['class_status'].str.upper() != 'CANCELLED'].copy()

    # Join Marks
    marks_merged = marks.merge(exams, on='exam_id', how='left')
    marks_merged = marks_merged.merge(
        students[['student_id', 'student_name', 'department', 'track_code', 'division', 'semester']],
        on='student_id', how='left'
    )
    marks_merged = marks_merged.merge(subjects[['subject_id', 'subject_name']], on='subject_id', how='left')

    # Evaluated status flag
    marks_merged['is_absent'] = marks_merged['result_status'].str.upper().isin(['ABSENT', 'AB']) | marks_merged['marks_numeric'].isna()
    marks_merged['is_evaluated'] = ~marks_merged['is_absent']
    marks_merged['is_passed'] = (marks_merged['result_status'].str.upper() == 'PASS') | (marks_merged['marks_numeric'] >= marks_merged['pass_marks'])
    marks_merged['norm_marks_pct'] = (marks_merged['marks_numeric'] / marks_merged['max_marks']) * 100

    return students, att_eligible, marks_merged, sessions, faculty, subjects, exams, calendar

# --- Load Data ---
data_file = "College_Analytics_Master_v3.xlsx"
if not os.path.exists(data_file):
    alt_file = os.path.join(os.getcwd(), "College_Analytics_Master_v3.xlsx")
    if os.path.exists(alt_file):
        data_file = alt_file
    else:
        st.error(f"Cannot find '{data_file}'. Make sure it is in the same folder as this script.")
        st.stop()

students_df, att_df, marks_df, sessions_df, faculty_df, subjects_df, exams_df, calendar_df = load_and_prepare_data(data_file)

# --- Sidebar Filters & Navigation ---
st.sidebar.title("🎛️ Navigation & Filters")
dashboard_selection = st.sidebar.radio(
    "Select Dashboard:",
    [
        "1. Academic Performance & Exam Analytics",
        "2. Attendance & Early-Warning System",
        "3. Faculty Workload & Course Delivery",
        "4. Academic Calendar & Syllabus Tracker",
        "5. 360° Individual Student Profile"
    ]
)

st.sidebar.markdown("---")
st.sidebar.subheader("Global Filters")

departments = sorted(students_df['department'].unique().tolist())
selected_dept = st.sidebar.multiselect("Department", departments, default=[])

tracks = sorted(students_df['track_code'].unique().tolist())
selected_track = st.sidebar.multiselect("Track Code", tracks, default=[])

divisions = sorted(students_df['division'].unique().tolist())
selected_div = st.sidebar.multiselect("Division", divisions, default=[])

# Apply filters
def filter_df(df):
    f_df = df.copy()
    if selected_dept and 'department' in f_df.columns:
        f_df = f_df[f_df['department'].isin(selected_dept)]
    if selected_track and 'track_code' in f_df.columns:
        f_df = f_df[f_df['track_code'].isin(selected_track)]
    if selected_div and 'division' in f_df.columns:
        f_df = f_df[f_df['division'].isin(selected_div)]
    return f_df

f_students = filter_df(students_df)
f_marks = filter_df(marks_df)
f_att = filter_df(att_df)

# ==============================================================================
# DASHBOARD 1: ACADEMIC PERFORMANCE & EXAM ANALYTICS
# ==============================================================================
if dashboard_selection.startswith("1."):
    st.title("📊 Student Academic Performance & Exam Analytics")
    st.caption("🎯 Audience: Principal, Dean, HODs & Examination Cell")

    total_students = f_students['student_id'].nunique()
    total_attempts = len(f_marks)
    evaluated_df = f_marks[f_marks['is_evaluated']]
    passed_df = evaluated_df[evaluated_df['is_passed']]
    absent_count = f_marks['is_absent'].sum()

    eval_attempts_count = len(evaluated_df)
    pass_pct = (len(passed_df) / eval_attempts_count * 100) if eval_attempts_count > 0 else 0
    absent_pct = (absent_count / total_attempts * 100) if total_attempts > 0 else 0
    avg_raw_marks = evaluated_df['marks_numeric'].mean() if eval_attempts_count > 0 else 0
    avg_norm_pct = evaluated_df['norm_marks_pct'].mean() if eval_attempts_count > 0 else 0

    kpi1, kpi2, kpi3, kpi4, kpi5, kpi6 = st.columns(6)
    kpi1.metric("Distinct Students", f"{total_students:,}")
    kpi2.metric("Evaluated Attempts", f"{eval_attempts_count:,}")
    kpi3.metric("Overall Pass %", f"{pass_pct:.1f}%")
    kpi4.metric("Avg Normalized %", f"{avg_norm_pct:.1f}%")
    kpi5.metric("Avg Raw Marks", f"{avg_raw_marks:.1f}")
    kpi6.metric("Exam Absentee %", f"{absent_pct:.1f}%")

    st.markdown("---")
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Assessment Comparisons (TA1, TA2, PBA1, PBA2, Final)")
        assess_summary = f_marks.groupby('exam_type').agg(
            total_attempts=('result_id', 'count'),
            evaluated=('is_evaluated', 'sum'),
            passed=('is_passed', 'sum'),
            absent=('is_absent', 'sum'),
            avg_raw=('marks_numeric', 'mean'),
            avg_norm=('norm_marks_pct', 'mean')
        ).reset_index()
        assess_summary['pass_pct'] = (assess_summary['passed'] / assess_summary['evaluated'] * 100).round(1)
        assess_summary['absent_pct'] = (assess_summary['absent'] / assess_summary['total_attempts'] * 100).round(1)

        fig_assess = px.bar(
            assess_summary,
            x='exam_type',
            y=['avg_norm', 'pass_pct'],
            barmode='group',
            labels={'value': 'Percentage (%)', 'exam_type': 'Assessment Type', 'variable': 'Metric'},
            title="Normalized Score % vs Pass % by Assessment",
            color_discrete_sequence=['#2563eb', '#10b981']
        )
        st.plotly_chart(fig_assess, use_container_width=True)

    with col2:
        st.subheader("Score Distribution")
        fig_dist = px.histogram(
            evaluated_df,
            x='norm_marks_pct',
            nbins=25,
            color='exam_type',
            labels={'norm_marks_pct': 'Normalized Marks (%)'},
            title="Score Distribution by Assessment Type",
            marginal="box"
        )
        st.plotly_chart(fig_dist, use_container_width=True)

    col3, col4 = st.columns(2)

    with col3:
        st.subheader("Track Performance Comparison")
        track_perf = evaluated_df.groupby('track_code').agg(
            students=('student_id', 'nunique'),
            pass_rate=('is_passed', lambda s: (s.sum() / len(s) * 100)),
            avg_score=('norm_marks_pct', 'mean')
        ).reset_index()

        fig_track = px.bar(
            track_perf,
            x='track_code',
            y='pass_rate',
            color='avg_score',
            color_continuous_scale='Blues',
            labels={'pass_rate': 'Pass Rate (%)', 'avg_score': 'Avg Score %', 'track_code': 'Track'},
            title="Pass Rate by Academic Track (Color = Avg Normalized Score)"
        )
        st.plotly_chart(fig_track, use_container_width=True)

    with col4:
        st.subheader("Subject-wise Performance & Difficulty Analysis")
        subj_perf = evaluated_df.groupby('subject_name').agg(
            evaluated_attempts=('result_id', 'count'),
            avg_norm_score=('norm_marks_pct', 'mean'),
            pass_rate=('is_passed', lambda s: (s.sum() / len(s) * 100))
        ).reset_index().sort_values(by='avg_norm_score', ascending=True)

        fig_subj = px.bar(
            subj_perf.head(10),
            x='avg_norm_score',
            y='subject_name',
            orientation='h',
            color='pass_rate',
            color_continuous_scale='RdYlGn',
            labels={'avg_norm_score': 'Avg Normalized Score (%)', 'subject_name': 'Subject', 'pass_rate': 'Pass %'},
            title="Lowest Performing Subjects (Support Priority)"
        )
        st.plotly_chart(fig_subj, use_container_width=True)

# ==============================================================================
# DASHBOARD 2: ATTENDANCE & EARLY-WARNING SYSTEM
# ==============================================================================
elif dashboard_selection.startswith("2."):
    st.title("🚨 Student Attendance & Engagement Early-Warning System")
    st.caption("🎯 Audience: Mentors, Class Teachers, Student Welfare & Parents")

    student_att_grouped = f_att.groupby(
        ['student_id', 'student_name', 'department', 'track_code', 'division', 'semester']
    ).agg(
        eligible_sessions=('attendance_id', 'count'),
        attended_sessions=('attendance_status', lambda s: s.str.upper().isin(['PRESENT', 'LATE']).sum()),
        present_sessions=('attendance_status', lambda s: (s.str.upper() == 'PRESENT').sum()),
        late_sessions=('attendance_status', lambda s: (s.str.upper() == 'LATE').sum()),
        absent_sessions=('attendance_status', lambda s: (s.str.upper() == 'ABSENT').sum()),
        scheduled_minutes=('scheduled_duration_minutes', 'sum'),
        attended_minutes=('minutes_attended', 'sum')
    ).reset_index()

    student_att_grouped['attendance_pct'] = (student_att_grouped['attended_sessions'] / student_att_grouped['eligible_sessions']) * 100
    student_att_grouped['missed_sessions'] = student_att_grouped['eligible_sessions'] - student_att_grouped['attended_sessions']
    student_att_grouped['hours_lost'] = (student_att_grouped['scheduled_minutes'] - student_att_grouped['attended_minutes']) / 60

    def categorize_risk(pct):
        if pct >= 75.0:
            return 'Safe (>=75%)'
        elif pct >= 65.0:
            return 'Warning (65-75%)'
        else:
            return 'Critical (<65%)'

    student_att_grouped['risk_category'] = student_att_grouped['attendance_pct'].apply(categorize_risk)

    total_monitored = len(student_att_grouped)
    overall_att_pct = (f_att['attendance_status'].str.upper().isin(['PRESENT', 'LATE']).sum() / len(f_att) * 100) if len(f_att) > 0 else 0
    safe_count = (student_att_grouped['risk_category'] == 'Safe (>=75%)').sum()
    warning_count = (student_att_grouped['risk_category'] == 'Warning (65-75%)').sum()
    critical_count = (student_att_grouped['risk_category'] == 'Critical (<65%)').sum()
    below_75_count = warning_count + critical_count
    total_lost_hours = student_att_grouped['hours_lost'].sum()

    kpi1, kpi2, kpi3, kpi4, kpi5, kpi6 = st.columns(6)
    kpi1.metric("Students Monitored", f"{total_monitored:,}")
    kpi2.metric("Overall Attendance", f"{overall_att_pct:.1f}%")
    kpi3.metric("Safe Cohort (>=75%)", f"{safe_count:,}", f"{(safe_count/total_monitored*100):.1f}%")
    kpi4.metric("Warning (65-75%)", f"{warning_count:,}", f"{(warning_count/total_monitored*100):.1f}%", delta_color="inverse")
    kpi5.metric("Critical Risk (<65%)", f"{critical_count:,}", f"{(critical_count/total_monitored*100):.1f}%", delta_color="inverse")
    kpi6.metric("Hours Lost", f"{total_lost_hours:,.0f} hrs")

    st.markdown("---")
    col_att1, col_att2 = st.columns(2)

    with col_att1:
        st.subheader("Attendance Risk Distribution")
        risk_counts = student_att_grouped['risk_category'].value_counts().reset_index()
        risk_counts.columns = ['Risk Category', 'Count']
        fig_pie = px.pie(
            risk_counts,
            names='Risk Category',
            values='Count',
            color='Risk Category',
            color_discrete_map={
                'Safe (>=75%)': '#10b981',
                'Warning (65-75%)': '#f59e0b',
                'Critical (<65%)': '#ef4444'
            },
            hole=0.45,
            title=f"Attendance Risk Categories ({below_75_count} Students Below 75%)"
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    with col_att2:
        st.subheader("Attendance vs. Final Marks Correlation")
        eval_student_scores = f_marks[f_marks['is_evaluated']].groupby('student_id')['norm_marks_pct'].mean().reset_index()
        scatter_df = student_att_grouped.merge(eval_student_scores, on='student_id', how='inner')

        fig_scatter = px.scatter(
            scatter_df,
            x='attendance_pct',
            y='norm_marks_pct',
            color='risk_category',
            color_discrete_map={
                'Safe (>=75%)': '#10b981',
                'Warning (65-75%)': '#f59e0b',
                'Critical (<65%)': '#ef4444'
            },
            labels={'attendance_pct': 'Attendance (%)', 'norm_marks_pct': 'Normalized Marks (%)', 'risk_category': 'Category'},
            hover_data=['student_id', 'student_name', 'division'],
            title="Attendance % vs Normalized Exam Score % (r = 0.53)"
        )
        fig_scatter.add_vline(x=75, line_dash="dash", line_color="orange", annotation_text="75% Safe Threshold")
        fig_scatter.add_vline(x=65, line_dash="dash", line_color="red", annotation_text="65% Detention Threshold")
        st.plotly_chart(fig_scatter, use_container_width=True)

    st.markdown("---")
    st.subheader("📋 Student Early-Warning & Risk Roster")

    filter_risk = st.selectbox(
        "Filter Roster by Risk Category:",
        ["All Students", "Below 75% Only (Critical & Warning)", "Critical (<65%) Only", "Warning (65-75%) Only", "Safe (>=75%) Only"]
    )

    roster_display = student_att_grouped.copy()
    if filter_risk == "Below 75% Only (Critical & Warning)":
        roster_display = roster_display[roster_display['risk_category'].isin(['Critical (<65%)', 'Warning (65-75%)'])]
    elif filter_risk == "Critical (<65%) Only":
        roster_display = roster_display[roster_display['risk_category'] == 'Critical (<65%)']
    elif filter_risk == "Warning (65-75%) Only":
        roster_display = roster_display[roster_display['risk_category'] == 'Warning (65-75%)']
    elif filter_risk == "Safe (>=75%) Only":
        roster_display = roster_display[roster_display['risk_category'] == 'Safe (>=75%)']

    roster_cols = [
        'student_id', 'student_name', 'department', 'track_code', 'division',
        'attendance_pct', 'risk_category', 'eligible_sessions', 'attended_sessions',
        'missed_sessions', 'late_sessions', 'hours_lost'
    ]
    roster_table = roster_display[roster_cols].sort_values(by='attendance_pct', ascending=True)

    st.dataframe(
        roster_table.style.format({
            'attendance_pct': '{:.1f}%',
            'hours_lost': '{:.1f} hrs'
        }),
        height=350,
        use_container_width=True
    )

    csv_data = roster_table.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Export Risk Roster to CSV",
        data=csv_data,
        file_name="student_attendance_early_warning_roster.csv",
        mime="text/csv"
    )

# ==============================================================================
# DASHBOARD 3: FACULTY WORKLOAD & COURSE DELIVERY
# ==============================================================================
elif dashboard_selection.startswith("3."):
    st.title("👩‍🏫 Faculty Workload & Course Delivery Dashboard")
    st.caption("🎯 Audience: Principal, HODs & IQAC")

    fac_sessions = sessions_df.merge(faculty_df, on='faculty_id', how='left')
    fac_sessions = fac_sessions.merge(subjects_df[['subject_id', 'subject_name']], on='subject_id', how='left')

    if selected_dept:
        fac_sessions = fac_sessions[fac_sessions['department'].isin(selected_dept)]
    if selected_track:
        fac_sessions = fac_sessions[fac_sessions['track_code'].isin(selected_track)]

    total_faculty = fac_sessions['faculty_id'].nunique()
    total_sess_scheduled = len(fac_sessions)
    total_sess_conducted = (fac_sessions['class_status'].str.upper() == 'CONDUCTED').sum()
    delivery_rate = (total_sess_conducted / total_sess_scheduled * 100) if total_sess_scheduled > 0 else 0
    total_teaching_hours = fac_sessions[fac_sessions['class_status'].str.upper() == 'CONDUCTED']['scheduled_duration_minutes'].sum() / 60

    fkpi1, fkpi2, fkpi3, fkpi4, fkpi5 = st.columns(5)
    fkpi1.metric("Active Faculty", f"{total_faculty}")
    fkpi2.metric("Scheduled Sessions", f"{total_sess_scheduled:,}")
    fkpi3.metric("Conducted Sessions", f"{total_sess_conducted:,}")
    fkpi4.metric("Course Delivery Rate", f"{delivery_rate:.1f}%")
    fkpi5.metric("Total Teaching Hours", f"{total_teaching_hours:,.0f} hrs")

    st.markdown("---")
    fcol1, fcol2 = st.columns(2)

    with fcol1:
        st.subheader("Workload by Faculty (Conducted vs Scheduled)")
        fac_workload = fac_sessions.groupby(['faculty_id', 'faculty_name', 'designation']).agg(
            scheduled_sessions=('session_id', 'count'),
            conducted_sessions=('class_status', lambda s: (s.str.upper() == 'CONDUCTED').sum()),
            teaching_hours=('scheduled_duration_minutes', lambda m: m.sum() / 60)
        ).reset_index().sort_values(by='conducted_sessions', ascending=False)

        fig_fac = px.bar(
            fac_workload.head(15),
            x='conducted_sessions',
            y='faculty_name',
            orientation='h',
            color='designation',
            labels={'conducted_sessions': 'Conducted Sessions', 'faculty_name': 'Faculty Member'},
            title="Top 15 Faculty by Sessions Conducted"
        )
        st.plotly_chart(fig_fac, use_container_width=True)

    with fcol2:
        st.subheader("Workload Type: Theory (Lecture) vs. Practical/Lab")
        type_dist = fac_sessions[fac_sessions['class_status'].str.upper() == 'CONDUCTED']['class_type'].value_counts().reset_index()
        type_dist.columns = ['Class Type', 'Count']
        fig_type = px.pie(
            type_dist,
            names='Class Type',
            values='Count',
            color='Class Type',
            color_discrete_map={'Lecture': '#3b82f6', 'Practical': '#10b981'},
            hole=0.4,
            title="Conducted Sessions by Type"
        )
        st.plotly_chart(fig_type, use_container_width=True)

    st.markdown("---")
    st.subheader("Faculty Seniority & Delivery Roster")
    st.dataframe(
        fac_workload.style.format({
            'teaching_hours': '{:.1f} hrs'
        }),
        height=320,
        use_container_width=True
    )

# ==============================================================================
# DASHBOARD 4: ACADEMIC CALENDAR & SYLLABUS PROGRESSION
# ==============================================================================
elif dashboard_selection.startswith("4."):
    st.title("📅 Academic Calendar & Syllabus Progression Tracker")
    st.caption("🎯 Audience: Academic Coordinators & Department Deans")

    total_cal_days = len(calendar_df)
    working_days = (calendar_df['is_working_day'].str.upper() == 'YES').sum()
    holidays = (calendar_df['event_type'].str.contains('Holiday|Weekend', case=False, na=False)).sum()
    exam_days = (calendar_df['event_type'].str.contains('Examination', case=False, na=False)).sum()

    # Milestone dates
    ta1_date = exams_df[exams_df['exam_type'] == 'TA1']['exam_date'].min()
    ta2_date = exams_df[exams_df['exam_type'] == 'TA2']['exam_date'].min()
    final_date = exams_df[exams_df['exam_type'] == 'Final']['exam_date'].min()

    sess_before_ta1 = (sessions_df['session_date'] < str(ta1_date)).sum()
    sess_before_ta2 = (sessions_df['session_date'] < str(ta2_date)).sum()
    sess_total = len(sessions_df)

    ckpi1, ckpi2, ckpi3, ckpi4, ckpi5 = st.columns(5)
    ckpi1.metric("Total Term Days", f"{total_cal_days}")
    ckpi2.metric("Working Teaching Days", f"{working_days}")
    ckpi3.metric("Holidays & Weekends", f"{holidays}")
    ckpi4.metric("Exam Window Days", f"{exam_days}")
    ckpi5.metric("Total Planned Classes", f"{sess_total:,}")

    st.markdown("---")
    ccol1, ccol2 = st.columns(2)

    with ccol1:
        st.subheader("Teaching Sessions Completed Before Assessment Milestones")
        milestone_data = pd.DataFrame({
            'Milestone': ['Before TA1', 'Before TA2', 'Before End-Sem'],
            'Completed Sessions': [sess_before_ta1, sess_before_ta2, sess_total],
            'Target Exam Date': [str(ta1_date), str(ta2_date), str(final_date)]
        })
        fig_mile = px.bar(
            milestone_data,
            x='Milestone',
            y='Completed Sessions',
            text='Completed Sessions',
            color='Milestone',
            color_discrete_sequence=['#60a5fa', '#3b82f6', '#1d4ed8'],
            title="Cumulative Teaching Sessions Completed"
        )
        st.plotly_chart(fig_mile, use_container_width=True)

    with ccol2:
        st.subheader("Academic Calendar Day Breakdown")
        cal_dist = calendar_df['event_type'].value_counts().reset_index()
        cal_dist.columns = ['Event Type', 'Days']
        fig_cal = px.pie(
            cal_dist,
            names='Event Type',
            values='Days',
            hole=0.4,
            title="Term Calendar Composition"
        )
        st.plotly_chart(fig_cal, use_container_width=True)

    st.markdown("---")
    st.subheader("Academic Calendar Master Schedule")
    st.dataframe(calendar_df, height=300, use_container_width=True)

# ==============================================================================
# DASHBOARD 5: 360° INDIVIDUAL STUDENT PROFILE
# ==============================================================================
else:
    st.title("👤 360° Individual Student Profile")
    st.caption("🎯 Audience: Mentors, Academic Advisors & Students")

    # Search / Select Student
    student_id_list = sorted(students_df['student_id'].unique().tolist())
    selected_student_id = st.selectbox("Search / Select Student ID:", student_id_list, index=0)

    # Student metadata
    s_meta = students_df[students_df['student_id'] == selected_student_id].iloc[0]
    st.markdown(f"""
    ### **{s_meta['student_name']}** (`{s_meta['student_id']}`)
    * **Department:** {s_meta['department']} | **Track:** {s_meta['track_code']} | **Division:** {s_meta['division']} | **Semester:** {s_meta['semester']}
    """)

    st.markdown("---")

    # Student Attendance metrics
    s_att = att_df[att_df['student_id'] == selected_student_id]
    s_total_sessions = len(s_att)
    s_present = (s_att['attendance_status'].str.upper() == 'PRESENT').sum()
    s_late = (s_att['attendance_status'].str.upper() == 'LATE').sum()
    s_absent = (s_att['attendance_status'].str.upper() == 'ABSENT').sum()
    s_attended = s_present + s_late
    s_att_pct = (s_attended / s_total_sessions * 100) if s_total_sessions > 0 else 0
    s_time_lost = (s_att['scheduled_duration_minutes'].sum() - s_att['minutes_attended'].sum()) / 60

    # Student Marks metrics
    s_marks = marks_df[marks_df['student_id'] == selected_student_id]
    s_eval_marks = s_marks[s_marks['is_evaluated']]
    s_avg_norm = s_eval_marks['norm_marks_pct'].mean() if len(s_eval_marks) > 0 else 0
    s_passed = s_eval_marks['is_passed'].sum()
    s_total_eval = len(s_eval_marks)
    s_pass_rate = (s_passed / s_total_eval * 100) if s_total_eval > 0 else 0

    scol1, scol2, scol3, scol4, scol5 = st.columns(5)
    scol1.metric("Attendance %", f"{s_att_pct:.1f}%")
    scol2.metric("Attended / Total", f"{s_attended} / {s_total_sessions}")
    scol3.metric("Avg Exam Score %", f"{s_avg_norm:.1f}%")
    scol4.metric("Exam Pass Rate", f"{s_pass_rate:.1f}%")
    scol5.metric("Time Lost (Late/Abs)", f"{s_time_lost:.1f} hrs")

    st.markdown("---")
    scol_left, scol_right = st.columns([1, 1])

    with scol_left:
        st.subheader("Attendance Status Gauge (vs 75% Requirement)")
        fig_gauge = go.Figure(go.Indicator(
            mode = "gauge+number",
            value = s_att_pct,
            title = {'text': "Attendance Percentage"},
            gauge = {
                'axis': {'range': [0, 100]},
                'bar': {'color': "#10b981" if s_att_pct >= 75 else ("#f59e0b" if s_att_pct >= 65 else "#ef4444")},
                'steps': [
                    {'range': [0, 65], 'color': "#fee2e2"},
                    {'range': [65, 75], 'color': "#fef3c7"},
                    {'range': [75, 100], 'color': "#d1fae5"}
                ],
                'threshold': {
                    'line': {'color': "black", 'width': 3},
                    'thickness': 0.75,
                    'value': 75
                }
            }
        ))
        fig_gauge.update_layout(height=280, margin=dict(t=40, b=10, l=20, r=20))
        st.plotly_chart(fig_gauge, use_container_width=True)

    with scol_right:
        st.subheader("Assessment Scorecard by Subject")
        subj_scorecard = s_marks[['subject_name', 'exam_type', 'marks_numeric', 'max_marks', 'result_status', 'norm_marks_pct']].dropna()
        fig_score = px.bar(
            subj_scorecard,
            x='exam_type',
            y='norm_marks_pct',
            color='subject_name',
            barmode='group',
            labels={'norm_marks_pct': 'Score (%)', 'exam_type': 'Exam Type'},
            title="Marks Obtained (%) Across Subjects"
        )
        fig_score.update_layout(height=280, margin=dict(t=40, b=10, l=20, r=20), legend_title_text='Subject')
        st.plotly_chart(fig_score, use_container_width=True)

    st.markdown("---")
    st.subheader("⏰ Late Arrival & Absenteeism Log")
    late_log = s_att[s_att['attendance_status'].str.upper().isin(['LATE', 'ABSENT'])][[
        'session_date', 'start_time', 'subject_name', 'attendance_status', 'scheduled_duration_minutes', 'minutes_attended'
    ]].copy()
    late_log['minutes_lost'] = late_log['scheduled_duration_minutes'] - late_log['minutes_attended']

    if len(late_log) > 0:
        st.dataframe(late_log.sort_values(by='session_date', ascending=False), height=240, use_container_width=True)
    else:
        st.success("🌟 Perfect punctuality record! No late or absent sessions recorded.")