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
    semester_date_options = generate_schedule.get_semesters()
    semester = st.selectbox("Semester", semester_date_options)
    col_day, col_start, col_end = st.columns(3)
    weekday_choices = WEEKDAYS.keys()
    weekday = col_day.selectbox("Wochentag", weekday_choices)
    start_time = col_start.time_input("Startzeit")
    end_time = col_end.time_input("Endzeit")
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
    with io.BytesIO() as outfile:
        schedule_df.to_excel(outfile, index=False)
        excel_file = outfile.getvalue()
    with io.StringIO() as outfile:
        schedule_df.to_markdown(outfile, index=False)
        markdown_file = outfile.getvalue()
    md_col, xl_col = st.columns(2)
    md_col.download_button(
        "Download Markdown",
        markdown_file,
        file_name="schedule.md",
        mime="text/markdown",
    )
    xl_col.download_button(
        "Download Excel",
        excel_file,
        file_name="schedule.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


if __name__ == "__main__":
    main()
