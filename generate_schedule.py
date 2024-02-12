#!/usr/bin/env python3

import argparse
import csv
import datetime
import json
import logging
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path

import arrow
from holidays.countries.germany import Germany

SEMESTER_FILE = Path("semester_dates.json")
LOCALE = "de-DE"


def _try_date(v):
    if isinstance(v, str):
        try:
            v = datetime.datetime.strptime(v, "%Y-%m-%d").date()
        except ValueError:
            pass
    elif isinstance(v, Sequence):
        return [_try_date(e) for e in v]
    return v


def _json_date_hook(o):
    for k, v in o.items():
        if isinstance(v, str):
            o[k] = _try_date(v)
        elif isinstance(v, Sequence):
            o[k] = [_try_date(e) for e in v]
        elif isinstance(v, Mapping):
            o[k] = _json_date_hook(v)
    return o


def annotate(date, breaks, state_holidays):
    date_arrow = arrow.Arrow.fromdate(date)
    for break_name, break_start, break_end in breaks:
        if date_arrow.is_between(
            arrow.Arrow.fromdate(break_start), arrow.Arrow.fromdate(break_end),
            bounds="[]"
        ):
            return (date, break_name)
    if date in state_holidays:
        return (date, state_holidays[date])
    return (date, None)


def get_semesters():
    with SEMESTER_FILE.open() as json_file:
        semester_dates = json.load(json_file, object_hook=_json_date_hook)
        return semester_dates.keys()


def get_semester_dates(semester):
    with SEMESTER_FILE.open() as json_file:
        semester_dates = json.load(json_file, object_hook=_json_date_hook)
    try:
        semester_dates = semester_dates[semester]
    except KeyError:
        logging.error(f'No dates found for semester "{semester}"!')
        raise
    return semester_dates


def generate_schedule(day, semester_dates):
    # Get first day of schedule
    lecture_period = semester_dates["lecture_period"]
    lecture_start, lecture_end = lecture_period
    schedule_start = arrow.util.next_weekday(lecture_start, day)
    # Get the end of the day for arrow’s range calculation
    lecture_end_arrow = arrow.Arrow.fromdate(lecture_end).ceil("day")
    # Get start and end time
    # TODO: Keep holiday/vacation dates but with comment
    schedule_dates = [
        d.date() for d in arrow.Arrow.range("week", schedule_start, lecture_end_arrow)
    ]
    return schedule_dates


def annotate_schedule(schedule_dates, semester_dates, state):
    lecture_period = semester_dates["lecture_period"]
    breaks = semester_dates["breaks"]
    # Get holidays for relevant years
    years = set(d.year for d in lecture_period)
    state_holidays = Germany(years)
    # Annotate each date
    return [annotate(date, breaks, state_holidays) for date in schedule_dates]


def filter_schedule(schedule_dates):
    return [date for date, annotation in schedule_dates if annotation is None]


def get_schedule_intervals(schedule_dates, start_time, end_time):
    return [
        (
            datetime.datetime.combine(date, start_time),
            datetime.datetime.combine(date, end_time),
        )
        for date in schedule_dates
    ]


def to_pandas(schedule_dates_annotated):
    import pandas as pd

    dates, annotations = zip(*schedule_dates_annotated)
    dates_formatted = []
    last_year = None
    for date in dates:
        date_arrow = arrow.Arrow.fromdate(date)
        if date.year == last_year:
            date_formatted = date_arrow.format("D.M.")
        else:
            date_formatted = date_arrow.format("D.M.YYYY")
            last_year = date.year
        dates_formatted.append(date_formatted)
    return pd.DataFrame(dict(Date=dates_formatted, Topic=annotations))


def main():
    # Parse commandline arguments
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("-v", "--verbose", action="store_true")
    arg_parser.add_argument("-s", "--semester", required=True)
    arg_parser.add_argument("-o", "--output", required=True)
    arg_parser.add_argument(
        "day", type=int, help="Day as number with Monday=0, Tuesday=1, ..."
    )
    arg_parser.add_argument("start_time", help="Format: HH:MM")
    arg_parser.add_argument("end_time", help="Format: HH:MM")
    args = arg_parser.parse_args()
    # Set up logging
    if args.verbose:
        level = logging.DEBUG
    else:
        level = logging.ERROR
    logging.basicConfig(level=level)
    # Determine output type
    outpath = Path(args.output)
    ext = outpath.suffix
    # Return exit value
    semester_dates = get_semester_dates(args.semester)
    schedule_dates = generate_schedule(args.day, semester_dates)
    schedule_dates_annotated = annotate_schedule(
        schedule_dates, semester_dates, state="NW"
    )
    if ext in (".md", ".xlsx"):
        schedule_df = to_pandas(schedule_dates_annotated)
        if ext == ".xlsx":
            schedule_df.to_excel(outpath, index=False)
        elif ext == ".md":
            schedule_df.to_markdown(outpath, index=False)
    elif ext == ".ics":
        schedule_dates_filtered = filter_schedule(schedule_dates_annotated)

        def convert_time(s):
            time_parts = tuple(int(p) for p in s.split(":"))
            return datetime.time(*time_parts)

        start_time = convert_time(args.start_time)
        end_time = convert_time(args.end_time)
        schedule_intervals = get_schedule_intervals(
            schedule_dates_filtered, start_time, end_time
        )
    else:
        print(f"Unknown output format {ext}.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
