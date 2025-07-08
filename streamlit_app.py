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
st.set_page_config(page_title="Attendance Tracker", page_icon="📊")
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

# Attendance Report
show_extras = False
if st.button("Generate Attendance Report"):
    show_extras = True
    st.header("📊 Attendance Report")
    subject_results = {}

    for subject in subjects:
        result = compute_subject_attendance(
            subject,
            past_counts.get(subject, 0),
            future_counts.get(subject, 0),
            attendance_data[subject]
        )
        subject_results[subject] = result

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

# 📈 Projected Attendance
# 📈 Projected Attendance — All Subjects
if show_extras:
    st.header("📈 Projected Attendance (per subject)")

    projected_data = []
    st.write("Enter how many future classes you think you'll attend for each subject (as count or estimated percentage).")

    for subj in subjects:
        st.subheader(f"{subj}")
        future_classes = future_counts[subj]
        input_mode = st.radio(f"Input mode for {subj}", ["Classes (count)", "Estimated %"], key=f"projmode_{subj}")

        if input_mode == "Classes (count)":
            projected_attend = st.number_input(f"Projected future classes to attend for {subj} (out of {future_classes})", 0, future_classes, key=f"projcount_{subj}")
        else:
            proj_percent = st.slider(f"Projected future attendance for {subj} (%)", 0, 100, 75, key=f"projperc_{subj}")
            projected_attend = math.floor((proj_percent / 100) * future_classes)
            st.info(f"🔹 {proj_percent}% → counted as {projected_attend} out of {future_classes}")

        past = past_counts[subj]
        attended = attendance_data[subj]
        total_future = projected_attend
        total_classes = past + future_classes
        projected_percent = ((attended + total_future) / total_classes) * 100 if total_classes > 0 else 0

        projected_data.append({
            "Subject": subj,
            "Projected Attendance %": round(projected_percent, 2)
        })

    # Plot
    df_proj = pd.DataFrame(projected_data)

    st.altair_chart(
        alt.Chart(df_proj).mark_bar().encode(
            x="Subject",
            y="Projected Attendance %",
            color=alt.condition(
                alt.datum["Projected Attendance %"] >= 75,
                alt.value("seagreen"), alt.value("orangered")
            )
        ).properties(height=350),
        use_container_width=True
    )

# 🟢 Bunk Day Recommender
if show_extras:
    st.header("🟢 Strategic Bunk Day Recommender")

    best_day = None
    best_attendance = None

    for day, subjects_on_day in class_schedule:
        if day <= today or not subjects_on_day or day.weekday() == 6 or day in holidays:
            continue

        temp_results = {}
        safe = True
        for subj in subjects:
            held = past_counts[subj]
            future = future_counts[subj]
            attended = attendance_data[subj]
            loss = subjects_on_day.count(subj) if subj in subjects_on_day else 0

            new_held = held
            new_future = future - loss
            new_attended = attended
            new_total = new_held + new_future
            new_percent = (new_attended / new_held * 100) if new_held else 0

            if new_total > 0 and (new_attended / new_total) < 0.75:
                safe = False
                break

            temp_results[subj] = (new_attended, new_total)

        if safe:
            best_day = day
            best_attendance = temp_results
            break

    if best_day:
        st.success(f"✅ Safest upcoming bunk day: {best_day.strftime('%A, %d %B %Y')}")
        st.write("📉 Your attendance would become:")
        for subj in subjects:
            held = past_counts[subj]
            future = future_counts[subj]
            attended = attendance_data[subj]
            loss = weekly_timetable[best_day.strftime("%A")].count(subj)
            new_total = held + future - loss
            new_percent = (attended / new_total * 100) if new_total > 0 else 0
            st.write(f"🔹 **{subj}** → {new_percent:.2f}%")
    else:
        st.info("No completely safe bunk days found based on current data.")

# 📬 Anonymous Feedback
st.header("📬 Anonymous Feedback")
feedback = st.text_area("Have suggestions, bugs, or anything to say?")
if st.button("Submit Feedback"):
    with open("feedback_log.txt", "a") as f:
        f.write(f"{date.today()} - {feedback}\n")
    st.success("Thanks! Feedback submitted anonymously.")
