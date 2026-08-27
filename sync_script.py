from datetime import datetime
import os
from icalendar import Calendar, Event
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import requests

# AUTHENTICATE WITH GOOGLE SHEETS
SCOPE = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]
CREDS = ServiceAccountCredentials.from_json_keyfile_name(
    "service_account.json", SCOPE
)
client = gspread.authorize(CREDS)
sheet = client.open("Master_Reservations").sheet1

ROOM_CALENDARS = {
    "202": "https://ical.booking.com/v1/export?t=d4901ddb-a6e3-4772-934b-f483e28df31a",
    "203": "https://ical.booking.com/v1/export?t=78ab5dab-fcf0-4525-9275-6c5b7c3cb4a4",
    "204": "https://ical.booking.com/v1/export?t=0686496b-239f-43ec-8043-2bed81df10db",
    "205": "https://ical.booking.com/v1/export?t=74ca24b8-34ce-4d50-94bd-1a70c240b28f",
    "206": "https://ical.booking.com/v1/export?t=ed352b48-3872-4606-ab95-54b2e3a1a1bb",
    "302": "https://ical.booking.com/v1/export?t=9c0e8743-522c-4a5a-bed8-3bc4a37731d2",
    "303": "https://ical.booking.com/v1/export?t=2d2a9ff2-d604-4b6e-a7eb-3a1451fd3c70",
    "304": "https://ical.booking.com/v1/export?t=34436506-196f-48f1-8bd2-e1adea36ff8e",
    "305": "https://ical.booking.com/v1/export?t=1d28628e-f036-4570-90d1-cd0591033bbc",
    "306": "https://ical.booking.com/v1/export?t=74773f81-7f30-401c-aa7b-4c7b49b98a0d",
}


# 1. PROCESS 1: PULL FROM BOOKING.COM & LOG TO SHEET
def sync_engine():
    print("Running sync_engine: Fetching updates from Booking.com...")
    existing_records = sheet.get_all_records()
    logged_uids = [str(record.get("UID")) for record in existing_records]

    new_entries_count = 0
    for room_number, url in ROOM_CALENDARS.items():
        response = requests.get(url)
        if response.status_code == 200:
            cal = Calendar.from_ical(response.text)
            for component in cal.walk("vevent"):
                uid = str(component.get("uid", ""))
                if uid and uid not in logged_uids:
                    dtstart = component.get("dtstart").dt
                    dtend = component.get("dtend").dt

                    if isinstance(dtstart, datetime):
                        dtstart = dtstart.date()
                    if isinstance(dtend, datetime):
                        dtend = dtend.date()

                    row_data = [
                        uid,
                        f"Room {room_number}",
                        "Booking.com",
                        "Booking.com Block",
                        dtstart.strftime("%Y-%m-%d"),
                        dtend.strftime("%Y-%m-%d"),
                        "Confirmed",
                    ]
                    sheet.append_row(row_data)
                    logged_uids.append(uid)
                    new_entries_count += 1

    print(f"-> Added {new_entries_count} new booking(s) to Google Sheet.")


# 2. PROCESS 2: EXPORT SHEET DATA TO LOCAL .ICS FILES
def export_ical():
    print("Running export_ical: Generating .ics files from Google Sheet...")
    records = sheet.get_all_records()
    rooms = ["202", "203", "204", "205", "206", "302", "303", "304", "305", "306"]
    os.makedirs("calendars", exist_ok=True)

    for room in rooms:
        cal = Calendar()
        cal.add("prodid", f"-//Hostal Santo Domingo Room {room}//")
        cal.add("version", "2.0")

        for row in records:
            sheet_room = str(row.get("Room", "")).replace("Room", "").strip()
            if sheet_room == room and row.get("Check-In") and row.get("Check-Out"):
                event = Event()
                event.add(
                    "summary", f"Reserved - {row.get('Guest Name', 'Guest')}"
                )
                event.add(
                    "dtstart",
                    datetime.strptime(
                        str(row.get("Check-In")), "%Y-%m-%d"
                    ).date(),
                )
                event.add(
                    "dtend",
                    datetime.strptime(
                        str(row.get("Check-Out")), "%Y-%m-%d"
                    ).date(),
                )
                event.add(
                    "uid",
                    str(row.get("UID", f"res-{room}-{row.get('Check-In')}")),
                )
                cal.add_component(event)

        with open(f"calendars/room_{room}.ics", "wb") as f:
            f.write(cal.to_ical())

    print("-> All room .ics files successfully updated in 'calendars/' folder.")


# MAIN EXECUTION: Runs both in order when triggered
if __name__ == "__main__":
    sync_engine()
    export_ical()
