import json
import time
from functools import wraps
from datetime import datetime, date, timedelta

import requests
from bs4 import BeautifulSoup

s = requests.Session()

# Change below
year_id = 75
semester_id = 2

# Cache for faculties and groups
faculty_cache = {}
group_cache = {}
schedule_cache = {}
CACHE_EXPIRY = timedelta(hours=2)


def track_time(func):

    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()
        print(f"Function {func.__name__} took {end_time - start_time:.2f} seconds")
        return result

    return wrapper


def replace_numbers(text):
    replacements = {'1': '1️⃣', '2': '2️⃣', '3': '3️⃣', '4': '4️⃣', '5': '5️⃣'}
    for num, emoji in replacements.items():
        text = text.replace(num, emoji)
    return text


@track_time
def get_faculties():
    global faculty_cache

    if faculty_cache and faculty_cache["expiry"] > datetime.now():
        return faculty_cache["data"]

    r = s.get(url="http://rasp.kart.edu.ua/schedule")
    soup = BeautifulSoup(r.text, 'html.parser')
    faculty_list = soup.find(id="schedule-search-faculty").find_all("option")
    faculties = {
        faculty.get("value"): faculty.text
        for faculty in faculty_list
        if faculty.get("value")
    }
    faculty_cache = {"data": faculties, "expiry": datetime.now() + CACHE_EXPIRY}
    return faculties


@track_time
def get_groups(faculty, course):
    global group_cache

    cache_key = (faculty, course)
    if cache_key in group_cache and group_cache[cache_key]["expiry"] > datetime.now():
        return group_cache[cache_key]["data"]

    headers = {
        "Accept": "*/*",
        "Content-Type": "application/x-www-form-urlencoded",
        "Origin": "http://rasp.kart.edu.ua",
        "Referer": "http://rasp.kart.edu.ua/schedule",
        "X-Requested-With": "XMLHttpRequest"
    }
    data = f"year_id={year_id}&faculty_id={faculty}&course_id={course}"
    r = s.post(url="http://rasp.kart.edu.ua/schedule/jdata", headers=headers, data=data)
    res_text = json.loads(r.text)
    groups = {team["id"]: team["title"] for team in res_text["teams"]}
    group_cache[cache_key] = {"data": groups, "expiry": datetime.now() + CACHE_EXPIRY}
    return groups


def check_week_and_day(week, week_day, day_name, res_text):
    name_subjects = {}
    name_id = 0
    change = False
    for subject in res_text["rows"]:
        row = subject["cell"]
        cur_week_pair = row[1]
        if day_name in ("Saturday", "Sunday"):
            change = True
            new_week_pair = "парн." if cur_week_pair == "непарн." else "непарн."
        else:
            new_week_pair = cur_week_pair
            change = False

        if (week == "Парна" and new_week_pair != "непарн.") or (
            week == "Непарна" and new_week_pair == "непарн."
        ):
            name_subject = row[int(week_day)]
            if name_subject:
                name_id += 1
                name_subjects[replace_numbers(str(name_id))] = name_subject

    return name_subjects, change


@track_time
def get_schedules(week, week_day, day_name, faculty_id, course_id, group_id):
    global schedule_cache

    cache_key = (week, week_day, day_name, faculty_id, course_id, group_id)
    if cache_key in schedule_cache and schedule_cache[cache_key]["expiry"] > datetime.now():
        return schedule_cache[cache_key]["data"]

    headers = {
        "Accept": "*/*",
        "Content-Type": "application/x-www-form-urlencoded",
        "Origin": "http://rasp.kart.edu.ua",
        "Referer": "http://rasp.kart.edu.ua/schedule",
        "X-Requested-With": "XMLHttpRequest"
    }
    time_now = str(round(time.time()))
    url = (
        f"http://rasp.kart.edu.ua/schedule/jsearch?year_id={year_id}&semester_id={semester_id}"
        f"&faculty_id={faculty_id}&course_id={course_id}&team_id={group_id}"
    )
    data = f"_search=false&nd={time_now}&rows=20&page=1&sidx=&sord=asc"
    r = s.post(url, data=data, headers=headers)
    res_text = json.loads(r.text)
    schedule, change = check_week_and_day(week, week_day, day_name, res_text)
    schedule_cache[cache_key] = {"data": (schedule, change), "expiry": datetime.now() + CACHE_EXPIRY}
    return schedule, change
