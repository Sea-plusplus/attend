import streamlit as st
import pandas as pd
import altair as alt
import math
from datetime import date, timedelta
from collections import defaultdict, Counter

# ============ CONFIGURATION ============
start_date = date(2025, 7, 14)
end_date = date(2025, 10, 30)
today = date.today()

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

# ============ STREAMLIT APP ============
st.set_page_config(page_title="Attendance Tracker", page_icon="")
st.markdown("### 👁️ Page Visits")
st.components.v1.html('''
<div align="center">
    <img src="https://hitwebcounter.com/counter/counter.php?page=1234567&style=0025&nbdigits=5&type=page&initCount=0" title="Web Counter" Alt="web counter" border="0" >
</div>
''', height=80)

st.title("Attendance Tracker")
st.write("Enter attendance for each subject to see whether you're safe or at risk.")

# Generate class data
holidays = expand_holidays(holiday_ranges)
working_days = get_working_days(start_date, end_date, holidays)
class_schedule = build_class_schedule(working_days, weekly_timetable)
past_counts, future_counts, future_dates = count_subjects_per_period(class_schedule)
subjects = sorted(set(past_counts) | set(future_counts))

# Attendance Input
st.header("Attendance Input")
attendance_data = {}

for subject in subjects:
    st.subheader(f"{subject}")
    input_mode = st.radio(f"Input mode for {subject}", ["Classes attended", "Estimated percentage"], key=f"{subject}_mode")
    held = past_counts.get(subject, 0)

    if input_mode == "Classes attended":
        count = st.number_input(f"Classes attended for {subject}", min_value=0, step=1, key=f"{subject}_count")
        attendance_data[subject] = int(count)
    else:
        percent = st.slider(f"Estimated attendance (%) for {subject}", 0, 100, step=1, key=f"{subject}_percent")
        estimated = math.floor((percent / 100) * held)
        actual_percent = (estimated / held * 100) if held else 0
        st.info(f"🔹 {percent}% → counted as {estimated} out of {held} ({actual_percent:.2f}%)")
        attendance_data[subject] = estimated

# Generate Report
if st.button("Generate Attendance Report"):
    st.header("Attendance Report")
    for subject in subjects:
        result = compute_subject_attendance(
            subject,
            past_counts.get(subject, 0),
            future_counts.get(subject, 0),
            attendance_data[subject]
        )

        st.subheader(f"{subject}")
        st.write(f"**Classes held:** {result['held']}")
        st.write(f"**Classes attended:** {result['attended']}")
        st.write(f"**Current percentage:** {result['percent']:.2f}%")
        st.write(f"**Future classes:** {result['future']}")
        st.write(f"**Must attend:** {result['needed']} (to not be detained)")

        if result['percent'] >= 75:
            st.success("You are currently above 75%. No further classes required.")
            bunks = max_bunks(result['attended'], result['held'], result['future'])
            st.info(f"You can afford to miss {bunks} classes before falling below 75%.")
        elif not result["can_reach"]:
            st.error("You cannot reach 75% even if you attend all remaining classes.")
        else:
            num_needed, date_needed = find_earliest_75(
                result['attended'], result['held'], future_dates[subject]
            )
            if date_needed:
                st.warning(f"You must attend the next {num_needed} classes to reach 75% by **{date_needed.strftime('%A, %d %B %Y')}**.")
            else:
                st.error("Even attending all classes won't help you reach 75%.")

# Projected Attendance Line Plot
st.header("📈 Projected Attendance Scenario")
future_plan = st.slider("If you attend __%__ of future classes", 0, 100, 75)

projection_data = []
for subject in subjects:
    held = past_counts[subject]
    future = future_counts[subject]
    attended = attendance_data[subject]
    total_future = (future_plan / 100) * future
    total = held + future
    projected_attended = attended + total_future
    projected_percent = (projected_attended / total * 100) if total > 0 else 0
    projection_data.append({
        "Subject": subject,
        "Projected %": round(projected_percent, 2)
    })

proj_df = pd.DataFrame(projection_data)
st.altair_chart(
    alt.Chart(proj_df).mark_bar().encode(
        x="Subject",
        y="Projected %",
        color=alt.condition(
            alt.datum["Projected %"] >= 75,
            alt.value("seagreen"), alt.value("orangered")
        )
    ).properties(height=350),
    use_container_width=True
)

# Bunk Recommender
st.header("🟢 Bunk Day Recommender (Safe Picks Only)")
safe_days = []

for day, subjects_on_day in class_schedule:
    if day <= today:
        continue
    if not subjects_on_day:
        continue

    is_safe = True
    for subj in subjects_on_day:
        att = attendance_data[subj]
        held = past_counts[subj]
        future = future_counts[subj]
        total = held + future
        if (att + future - 1) / total < 0.75:
            is_safe = False
            break

    if is_safe:
        safe_days.append(day.strftime("%A, %d %B"))

if safe_days:
    st.write("You can safely bunk on:")
    for d in safe_days[:5]:
        st.success(f"✅ {d}")
else:
    st.info("No completely safe bunk days based on current data.")

# Feedback box
st.header("📬 Anonymous Feedback")
feedback = st.text_area("Have suggestions, bugs, or anything to say?")
if st.button("Submit Feedback"):
    with open("feedback_log.txt", "a") as f:
        f.write(f"{date.today()} - {feedback}\n")
    st.success("Thanks! Feedback submitted anonymously.")
