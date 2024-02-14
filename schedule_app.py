#!/usr/bin/env python

import argparse
import io
import logging
import sys

import generate_schedule
import streamlit as st

WEEKDAYS = dict(
    (
        ("Montag", 0),
        ("Dienstag", 1),
        ("Mittwoch", 2),
        ("Donnerstag", 3),
        ("Freitag", 4),
        ("Samstag", 5),
        ("Sonntag", 6),
    )
)


def main():
    st.title("Seminarplan-Generator")
    # Inputs
    semester_date_options = generate_schedule.get_semesters()
    semester = st.selectbox("Semester", semester_date_options)
    course_name = st.text_input("Name der Veranstaltung")
    col_day, col_start, col_end = st.columns(3)
    weekday_choices = WEEKDAYS.keys()
    weekday = col_day.selectbox("Wochentag", weekday_choices)
    start_time = col_start.time_input("Startzeit")
    end_time = col_end.time_input("Endzeit")
    # Output
    st.write(f"Zeitplan für {weekday} von {start_time} bis {end_time}")
    semester_dates = generate_schedule.get_semester_dates(semester)
    schedule_dates = generate_schedule.generate_schedule(
        WEEKDAYS[weekday], semester_dates
    )
    schedule_dates_annotated = generate_schedule.annotate_schedule(
        schedule_dates, semester_dates, state="NW"
    )
    schedule_df = generate_schedule.to_pandas(schedule_dates_annotated)
    st.dataframe(
        schedule_df,
        hide_index=True,
        use_container_width=True,
        column_config={"Date": "Datum", "Topic": "Thema"},
    )
    # Downloads
    filename_base = "-".join(course_name.lower().replace("/", "-").split())
    with io.BytesIO() as outfile:
        schedule_df.to_excel(outfile, index=False)
        excel_file = outfile.getvalue()
    with io.StringIO() as outfile:
        schedule_df.to_markdown(outfile, index=False)
        markdown_file = outfile.getvalue()
    md_col, xl_col, col_ics = st.columns(3)
    md_col.download_button(
        "Download Markdown",
        markdown_file,
        file_name=f"{filename_base}.md",
        mime="text/markdown",
    )
    xl_col.download_button(
        "Download Excel",
        excel_file,
        file_name=f"{filename_base}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    schedule_dates_filtered = generate_schedule.filter_schedule(
        schedule_dates_annotated
    )
    schedule_intervals = generate_schedule.get_schedule_intervals(
        schedule_dates_filtered, start_time, end_time
    )
    cal = generate_schedule.to_ical(schedule_intervals, name=course_name)
    col_ics.download_button(
        "Download ICS",
        cal.to_ical(),
        file_name=f"{filename_base}.ics",
        mime="text/calendar",
    )
    st.divider()
    st.caption(
        "Erstellt von Frederik Elwert. Diese App berücksichtigt derzeit "
        "die Semesterzeiten der Ruhr-Uni Bochum "
        "und Feiertage in NRW. Der Code liegt auf "
        "[GitHub](https://github.com/frederik-elwert/schedule-generator) und darf "
        "gerne angepasst werden."
    )


if __name__ == "__main__":
    main()
