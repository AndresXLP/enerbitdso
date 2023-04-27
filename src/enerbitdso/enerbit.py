import datetime as dt
import logging

import httpx
import pydantic
import urlpath

logger = logging.getLogger(__name__)


TIMEOUT = httpx.Timeout(5, read=60)

WATT_HOUR_TO_KILOWATT_HOUR = 0.001


class ScheduleUsageRecord(pydantic.BaseModel):
    frt_code: str
    meter_serial: str
    time_start: dt.datetime
    time_end: dt.datetime
    active_energy_imported: float
    active_energy_exported: float
    reactive_energy_imported: float
    reactive_energy_exported: float


class ScheduleMeasurementRecord(pydantic.BaseModel):
    frt_code: str
    meter_serial: str
    time_local_utc: dt.datetime
    voltage_multiplier: float
    current_multiplier: float
    active_energy_imported: float
    active_energy_exported: float
    reactive_energy_imported: float
    reactive_energy_exported: float


def get_auth_token(base_url, username, password):
    path = "/auth/token/"
    data = {"username": username, "password": password}
    with httpx.Client(base_url=base_url) as client:
        response = client.post(path, data=data)
        response.raise_for_status()
    token = response.json()["access_token"]
    return token


def get_client(base_url, username, password):
    url = str(urlpath.URL(base_url))
    token = get_auth_token(url, username, password)
    auth = {"Authorization": f"Bearer {token}"}
    return httpx.Client(base_url=url, headers=auth, timeout=TIMEOUT)


def scale_measurement_records(records: list[ScheduleMeasurementRecord], scale: float):
    for r in records:
        r.active_energy_imported = r.active_energy_imported * scale
        r.active_energy_exported = r.active_energy_exported * scale
        r.reactive_energy_imported = r.reactive_energy_imported * scale
        r.reactive_energy_exported = r.reactive_energy_exported * scale
    return records


def scale_usage_records(records: list[ScheduleUsageRecord], scale: float):
    for r in records:
        r.active_energy_imported = r.active_energy_imported * scale
        r.active_energy_exported = r.active_energy_exported * scale
        r.reactive_energy_imported = r.reactive_energy_imported * scale
        r.reactive_energy_exported = r.reactive_energy_exported * scale
    return records


def get_schedule_usage_records(
    client: httpx.Client, frt_code: str, since: dt.datetime, until: dt.datetime
) -> list[ScheduleUsageRecord]:
    path = "/measurements/schedules/usages"
    params = {
        "since": since,
        "until": until,
        "frt-code": frt_code,
        "period-string": "hour",
        "period-number": 1,
    }
    response = client.get(path, params=params)
    response.raise_for_status()
    records = response.json()
    records = sorted(records, key=lambda r: r["time_start"])
    usage_records = [ScheduleUsageRecord.parse_obj(r) for r in records]
    usage_records = scale_usage_records(usage_records, scale=WATT_HOUR_TO_KILOWATT_HOUR)
    return usage_records


def get_schedule_measurement_records(
    client: httpx.Client, frt_code: str, since: dt.datetime, until: dt.datetime
) -> list[ScheduleMeasurementRecord]:
    path = "/measurements/schedules/"
    params = {
        "since": since,
        "until": until,
        "frt-code": frt_code,
    }
    response = client.get(path, params=params)
    response.raise_for_status()
    records = response.json()
    records = sorted(records, key=lambda r: r["time_local_utc"])
    measurement_records = [ScheduleMeasurementRecord.parse_obj(r) for r in records]
    measurement_records = scale_measurement_records(
        measurement_records, scale=WATT_HOUR_TO_KILOWATT_HOUR
    )
    return measurement_records
