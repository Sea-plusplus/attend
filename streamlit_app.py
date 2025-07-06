import streamlit as st
from datetime import date, timedelta
import math
from collections import defaultdict, Counter

# ============ CONFIGURATION ============
start_date = date(2025, 7, 14)
end_date = date(2025, 10, 30)
today = date(2025, 8, 17)  # set to fixed date for testing

weekly_timetable = {
    "Monday":    ["Math", "Physics"],
    "Tuesday":   ["English", "English"],
    "Wednesday": ["Math", "Math", "CS"],
    "Thursday":  ["Physics"],
    "Friday":    ["Math", "CS"],
    "Saturday":  [],
}

holiday_ranges = [
    (date(2025, 8, 15), date(2025, 8, 16)),
    (date(2025, 8, 20), date(2025, 8, 22)),
    (date(2025, 8, 27), date(2025, 8, 27)),
    (date(2025, 9, 4), date(2025, 9, 10)),
    (date(2025, 9, 29), date(2025, 9, 30)),
    (date(2025, 10, 1), date(2025, 10, 2)),
    (date(2025, 10, 16), date(2025, 10, 20)),
]

# ============ FUNCTIONS ============
def expand_holidays(ranges):
    holidays = set()
    for start, end in ranges:
        for offset in range((end - start).days + 1):
            holidays.add(start + timedelta(days=offset))
    return holidays

def get_working_days(start, end, holidays):
    return [
        d for d in (start + timedelta(days=i) for i in range((end - start).days + 1))
        if d.weekday() != 6 and d not in holidays
    ]

def build_class_schedule(working_days, timetable):
    weekday_map = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
    all_classes = []
    for day in working_days:
        weekday_name = weekday_map[day.weekday()]
        subjects = timetable.get(weekday_name, [])
        all_classes.append((day, subjects))
    return all_classes

def count_subjects_per_period(class_schedule):
    past_counts = Counter()
    future_counts = Counter()
    future_dates = defaultdict(list)
    for day, subjects in class_schedule:
        for subj in subjects:
            if day <= today:
                past_counts[subj] += 1
            else:
                future_counts[subj] += 1
                future_dates[subj].append(day)
    return past_counts, future_counts, future_dates

def compute_subject_attendance(subject, past, future, attended):
    T = past
    F = future
    A = attended
    total_classes = T + F
    required_total = 0.75 * total_classes
    needed = max(0, math.ceil(required_total - A))
    current_percent = (A / T * 100) if T > 0 else 0
    can_reach = needed <= F
    return {
        "held": T,
        "attended": A,
        "percent": current_percent,
        "future": F,
        "needed": needed,
        "can_reach": can_reach
    }

def find_earliest_75(attended, held, future_dates):
    total = held
    present = attended
    for i, day in enumerate(future_dates):
        present += 1
        total += 1
        if (present / total) * 100 >= 75:
            return i + 1, day
    return None, None

def max_bunks(attended, held, future):
    total = held + future
    return max(0, math.floor(attended + future - 0.75 * total))

# ============ STYLED STREAMLIT UI ============
st.set_page_config(page_title="Attendance Terminal", layout="centered")

st.markdown("""
    <style>
    body {
        background-color: #000;
        color: #00FF99;
        font-family: monospace;
    }
    .report-box {
        background: #111;
        border: 1px solid #0f0;
        padding: 1em;
        margin-bottom: 1.5em;
        border-radius: 5px;
        box-shadow: 0 0 10px #0f0a;
    }
    .ascii-header {
        color: #0f0;
        font-family: monospace;
        white-space: pre;
        font-size: 12px;
    }
    .badge-grid {
        display: flex;
        flex-wrap: wrap;
        gap: 5px;
        justify-content: center;
        margin-top: 1em;
    }
    .badge-grid img {
        image-rendering: pixelated;
        height: 31px;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="ascii-header">
    ___________  ___________________  _______
==== 4C 45 54 / ___       |/    __  / /    _   |/    __/ 4C 4F 56 ====
=/=/=/=/=/ 53 20 41 /__  /  /  , ' /  __/ / / /  _  | ' /  __/ 45 20 4C /=/=/=/=/=
==== 4C 4C 20 /____/__/__/|__/____/_____/__/__/|__/____/ 41 49 4E ====

   ==// WELCOME, USER //======// YOU ARE SAFE HERE //==
</div>
""", unsafe_allow_html=True)

holidays = expand_holidays(holiday_ranges)
working_days = get_working_days(start_date, end_date, holidays)
class_schedule = build_class_schedule(working_days, weekly_timetable)
past_counts, future_counts, future_dates = count_subjects_per_period(class_schedule)
subjects = sorted(set(past_counts) | set(future_counts))

st.header("Input Attendance")
attendance_data = {}
for subject in subjects:
    st.subheader(f"{subject}")
    mode = st.radio("Input mode", ["Count", "%"], key=f"{subject}_mode")
    held = past_counts.get(subject, 0)
    if mode == "%":
        percent = st.slider(f"Estimated % for {subject}", 0, 100, 0, 1)
        attendance_data[subject] = math.floor((percent/100)*held)
    else:
        attendance_data[subject] = st.number_input(f"Attended for {subject}", min_value=0, step=1, key=f"{subject}_count")

if st.button("Generate Report"):
    for subject in subjects:
        result = compute_subject_attendance(
            subject,
            past_counts.get(subject, 0),
            future_counts.get(subject, 0),
            attendance_data[subject]
        )
        st.markdown(f"""
        <div class=\"report-box\">
        <b>Subject:</b> {subject}<br>
        Classes held: {result['held']}<br>
        Classes attended: {result['attended']}<br>
        Current %: {result['percent']:.2f}%<br>
        Future classes: {result['future']}<br>
        Must attend: {result['needed']}<br>
        """, unsafe_allow_html=True)

        if result['percent'] >= 75:
            bunks = max_bunks(result['attended'], result['held'], result['future'])
            st.markdown(f"✅ You are safe. You can miss {bunks} more classes.</div>", unsafe_allow_html=True)
        elif not result["can_reach"]:
            st.markdown("❌ Cannot reach 75% even with full attendance.</div>", unsafe_allow_html=True)
        else:
            needed, day = find_earliest_75(result['attended'], result['held'], future_dates[subject])
            st.markdown(f"⚠️ Attend next {needed} to reach 75% by {day.strftime('%A, %d %B %Y')}</div>", unsafe_allow_html=True)

st.markdown("""
<div style='margin-top: 3em; text-align: center; color: #0f0;'>
    Present day, Present time — 2025<br>
    <a href="https://github.com/adryd325/oneko.js" style="color:#0f0; text-decoration:none">oneko.js by adryd325</a>
    <div class='badge-grid'>
        <img src='https://sinewave.cyou/cdn/badges/sinewave.gif'>
        <img src='https://sinewave.cyou/cdn/badges/eggbug.gif'>
        <img src='https://sinewave.cyou/cdn/badges/versarytown.png'>
        <img src='https://sinewave.cyou/cdn/badges/oatzone.gif'>
        <img src='https://sinewave.cyou/cdn/badges/maia.png'>
        <img src='https://sinewave.cyou/cdn/badges/void.gif'>
        <img src='https://sinewave.cyou/cdn/badges/noweb3.gif'>
        <img src='https://sinewave.cyou/cdn/badges/neovim.gif'>
    </div>
</div>
""", unsafe_allow_html=True)


