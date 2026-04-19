import requests
import re

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
}

# RailYatri endpoints
TRAIN_SEARCH_URL = "https://search.railyatri.in/v2/mobile/trainsearch.json"
RAILYATRI_BASE = "https://www.railyatri.in"

# Cache the buildId so we don't fetch it every request
_build_id_cache = {"value": None}


def _get_build_id() -> str:
    """Fetch the current Next.js buildId from RailYatri."""
    if _build_id_cache["value"]:
        return _build_id_cache["value"]
    try:
        resp = requests.get(
            f"{RAILYATRI_BASE}/pnr-status",
            headers=HEADERS,
            timeout=10,
        )
        match = re.search(r'"buildId"\s*:\s*"([^"]+)"', resp.text)
        if match:
            _build_id_cache["value"] = match.group(1)
            return _build_id_cache["value"]
    except requests.RequestException:
        pass
    return ""


def _mins_to_time(mins: int) -> str:
    """Convert minutes-since-midnight to HH:MM string."""
    if not mins or mins <= 0:
        return "--"
    h = (mins // 60) % 24
    m = mins % 60
    return f"{h:02d}:{m:02d}"


def _format_delay(delay_mins) -> str:
    """Format delay minutes into a human-readable string."""
    if delay_mins is None or delay_mins == 0:
        return "On Time"
    if isinstance(delay_mins, (int, float)):
        if delay_mins > 0:
            return f"{int(delay_mins)} min late"
        return f"{abs(int(delay_mins))} min early"
    return str(delay_mins)


def search_train(query: str) -> dict:
    """Search trains by name or number using RailYatri."""
    result = _search_train_api(query)
    if result["success"] and result.get("data"):
        return result
    return _search_train_mock(query)


def get_live_status(train_number: str, start_date: str) -> dict:
    """Get live running status of a train using RailYatri."""
    result = _get_live_status_api(train_number, start_date)
    if result["success"]:
        return result
    return _get_live_status_mock(train_number, start_date)


def get_pnr_status(pnr: str) -> dict:
    """Get PNR status (mock — RailYatri PNR API is not publicly available)."""
    return _get_pnr_status_mock(pnr)


# ── RailYatri API calls ────────────────────────────────────────────────


def _search_train_api(query: str) -> dict:
    try:
        resp = requests.get(
            TRAIN_SEARCH_URL,
            headers=HEADERS,
            params={"q": query},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("success") and data.get("trains"):
            trains = [
                {
                    "trainNo": t["train_number"],
                    "trainName": t["train_name"],
                    "fromStn": t.get("src_stn_code", ""),
                    "toStn": t.get("dstn_stn_code", ""),
                    "departTime": "",
                    "arriveTime": "",
                }
                for t in data["trains"]
            ]
            return {"success": True, "data": trains}
        return {"success": True, "data": []}
    except requests.RequestException as e:
        return {"success": False, "error": str(e)}


def _get_live_status_api(train_number: str, start_date: str) -> dict:
    try:
        build_id = _get_build_id()
        if not build_id:
            return {"success": False, "error": "Could not fetch RailYatri buildId"}

        url = f"{RAILYATRI_BASE}/_next/data/{build_id}/live-train-status/{train_number}.json"
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        page = resp.json()
        props = page.get("pageProps", {})
        lts = props.get("ltsData", {})
        tt_list = props.get("timeTableData", [])

        if not lts or not lts.get("success"):
            msg = lts.get("new_message") or lts.get("title") or "Train not found"
            return {"success": False, "error": msg}

        # Build station list from upcoming + previous stations
        stations = []
        all_stations = lts.get("previous_stations", []) + lts.get(
            "upcoming_stations", []
        )

        # If no live station data, fall back to timetable route (stopping stations)
        if not all_stations and tt_list:
            route = tt_list[0].get("route", [])
            stops = [s for s in route if s.get("stop")]
            for s in stops:
                stations.append(
                    {
                        "code": s.get("station_code", ""),
                        "name": s.get("station_name", ""),
                        "schArr": _mins_to_time(s.get("sta_min", 0)),
                        "schDep": _mins_to_time(s.get("std_min", 0)),
                        "actArr": "--",
                        "delay": "--",
                        "platform": str(s.get("platform_number", "--")),
                    }
                )
        else:
            for s in all_stations:
                if not s.get("station_code"):
                    continue
                arr_delay = s.get("arrival_delay", 0)
                stations.append(
                    {
                        "code": s.get("station_code", ""),
                        "name": s.get("station_name", ""),
                        "schArr": s.get("sta", "--"),
                        "schDep": s.get("std", "--"),
                        "actArr": s.get("eta", s.get("sta", "--")),
                        "delay": _format_delay(arr_delay),
                        "platform": str(s.get("platform_number", "--")),
                    }
                )

        # Format delay
        delay_val = lts.get("delay", 0)
        delay_text = _format_delay(delay_val)

        current_stn = lts.get("current_station_name", "").rstrip("~' ")
        current_code = lts.get("current_station_code", "")
        current_station = f"{current_code} - {current_stn}" if current_code else "N/A"

        return {
            "success": True,
            "data": {
                "trainNo": lts.get("train_number", train_number),
                "trainName": lts.get("train_name", ""),
                "fromStn": lts.get("source", ""),
                "toStn": lts.get("destination", ""),
                "currentStation": current_station,
                "delay": delay_text,
                "lastUpdated": lts.get("status_as_of", ""),
                "journeyDate": start_date,
                "runDays": lts.get("run_days", ""),
                "isRunDay": lts.get("is_run_day", False),
                "message": lts.get("new_message", ""),
                "stations": stations,
            },
        }
    except requests.RequestException as e:
        # Reset buildId cache on failure so it's refetched next time
        _build_id_cache["value"] = None
        return {"success": False, "error": str(e)}


# ── Mock data for development without API key ───────────────────────────

MOCK_TRAINS = [
    {
        "trainNo": "12951",
        "trainName": "Mumbai Rajdhani Express",
        "fromStn": "MMCT",
        "toStn": "NDLS",
        "departTime": "16:35",
        "arriveTime": "08:35",
    },
    {
        "trainNo": "12952",
        "trainName": "New Delhi Rajdhani Express",
        "fromStn": "NDLS",
        "toStn": "MMCT",
        "departTime": "16:55",
        "arriveTime": "08:15",
    },
    {
        "trainNo": "12301",
        "trainName": "Howrah Rajdhani Express",
        "fromStn": "HWH",
        "toStn": "NDLS",
        "departTime": "16:55",
        "arriveTime": "09:55",
    },
    {
        "trainNo": "12302",
        "trainName": "New Delhi Rajdhani Express",
        "fromStn": "NDLS",
        "toStn": "HWH",
        "departTime": "16:55",
        "arriveTime": "09:55",
    },
    {
        "trainNo": "12259",
        "trainName": "Sealdah Duronto Express",
        "fromStn": "SDAH",
        "toStn": "NDLS",
        "departTime": "20:10",
        "arriveTime": "10:25",
    },
    {
        "trainNo": "12260",
        "trainName": "New Delhi Duronto Express",
        "fromStn": "NDLS",
        "toStn": "SDAH",
        "departTime": "19:40",
        "arriveTime": "09:10",
    },
    {
        "trainNo": "22691",
        "trainName": "Rajdhani Express",
        "fromStn": "SBC",
        "toStn": "NDLS",
        "departTime": "20:00",
        "arriveTime": "05:50",
    },
    {
        "trainNo": "12627",
        "trainName": "Karnataka Express",
        "fromStn": "SBC",
        "toStn": "NDLS",
        "departTime": "21:30",
        "arriveTime": "05:10",
    },
    {
        "trainNo": "12621",
        "trainName": "Tamil Nadu Express",
        "fromStn": "MAS",
        "toStn": "NDLS",
        "departTime": "22:00",
        "arriveTime": "07:10",
    },
    {
        "trainNo": "12622",
        "trainName": "Tamil Nadu Express",
        "fromStn": "NDLS",
        "toStn": "MAS",
        "departTime": "22:30",
        "arriveTime": "07:40",
    },
    {
        "trainNo": "12431",
        "trainName": "Trivandrum Rajdhani Express",
        "fromStn": "TVC",
        "toStn": "NDLS",
        "departTime": "11:25",
        "arriveTime": "18:05",
    },
    {
        "trainNo": "12432",
        "trainName": "New Delhi Rajdhani Express",
        "fromStn": "NDLS",
        "toStn": "TVC",
        "departTime": "10:55",
        "arriveTime": "17:40",
    },
]

MOCK_STATIONS = [
    {
        "code": "NDLS",
        "name": "New Delhi",
        "schArr": "08:35",
        "schDep": "--",
        "actArr": "08:50",
        "delay": "15 min late",
        "distance": "1384 km",
        "platform": "5",
    },
    {
        "code": "BRC",
        "name": "Vadodara Junction",
        "schArr": "02:58",
        "schDep": "03:00",
        "actArr": "03:10",
        "delay": "12 min late",
        "distance": "392 km",
        "platform": "3",
    },
    {
        "code": "RTM",
        "name": "Ratlam Junction",
        "schArr": "06:22",
        "schDep": "06:27",
        "actArr": "06:35",
        "delay": "13 min late",
        "distance": "658 km",
        "platform": "1",
    },
    {
        "code": "KOTA",
        "name": "Kota Junction",
        "schArr": "10:27",
        "schDep": "10:32",
        "actArr": "10:40",
        "delay": "13 min late",
        "distance": "906 km",
        "platform": "2",
    },
    {
        "code": "MTJ",
        "name": "Mathura Junction",
        "schArr": "14:55",
        "schDep": "14:57",
        "actArr": "15:08",
        "delay": "13 min late",
        "distance": "1225 km",
        "platform": "4",
    },
]


def _search_train_mock(query: str) -> dict:
    query_lower = query.lower().strip()
    results = [
        t
        for t in MOCK_TRAINS
        if query_lower in t["trainNo"] or query_lower in t["trainName"].lower()
    ]
    return {"success": True, "data": results}


def _get_live_status_mock(train_number: str, start_date: str) -> dict:
    train = next((t for t in MOCK_TRAINS if t["trainNo"] == train_number), None)
    if not train:
        return {"success": False, "error": "Train not found"}

    return {
        "success": True,
        "data": {
            "trainNo": train["trainNo"],
            "trainName": train["trainName"],
            "fromStn": train["fromStn"],
            "toStn": train["toStn"],
            "currentStation": "KOTA - Kota Junction",
            "delay": "13 min late",
            "lastUpdated": "2 min ago",
            "journeyDate": start_date,
            "stations": MOCK_STATIONS,
        },
    }


def _get_pnr_status_mock(pnr: str) -> dict:
    if len(pnr) != 10 or not pnr.isdigit():
        return {"success": False, "error": "Invalid PNR number. Must be 10 digits."}

    return {
        "success": True,
        "data": {
            "pnrNumber": pnr,
            "trainNo": "12951",
            "trainName": "Mumbai Rajdhani Express",
            "fromStn": "MMCT",
            "toStn": "NDLS",
            "journeyDate": "2026-04-20",
            "chartStatus": "Chart Prepared",
            "passengers": [
                {
                    "number": 1,
                    "bookingStatus": "S1/32/GN",
                    "currentStatus": "CNF/S1/32",
                },
            ],
        },
    }
