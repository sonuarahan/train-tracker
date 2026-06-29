"""
PNR Status Service
Handles PNR validation and data extraction from RailYatri API
"""

import requests
import re
from typing import Optional, Dict, Any
from constants import (
    RAILYATRI_BASE_URL,
    DEFAULT_HEADERS,
    API_TIMEOUT,
    BUILD_ID_TIMEOUT,
    DEMO_PNR_1,
    DEMO_PNR_2,
)


class PNRService:
    """Service for fetching and processing PNR status"""

    def __init__(self):
        self._build_id_cache: Optional[str] = None

    def _get_build_id(self) -> Optional[str]:
        """
        Fetch the current Next.js buildId from RailYatri.
        Uses cached value if available.
        """
        if self._build_id_cache:
            return self._build_id_cache

        try:
            resp = requests.get(
                f"{RAILYATRI_BASE_URL}/pnr-status",
                headers=DEFAULT_HEADERS,
                timeout=BUILD_ID_TIMEOUT,
            )
            resp.raise_for_status()

            # Extract buildId from HTML response
            match = re.search(r'"buildId"\s*:\s*"([^"]+)"', resp.text)
            if match:
                self._build_id_cache = match.group(1)
                return self._build_id_cache
        except requests.RequestException as e:
            print(f"Build ID fetch error: {e}")

        return None

    def _reset_build_id_cache(self) -> None:
        """Reset the buildId cache on API failure"""
        self._build_id_cache = None

    def get_pnr_status_from_api(self, pnr: str) -> Dict[str, Any]:
        """
        Fetch PNR status from RailYatri API.
        Returns structured response with train details.
        """
        if not self._validate_pnr(pnr):
            return {
                "success": False,
                "error": "Invalid PNR number. Must be 10 digits.",
            }

        build_id = self._get_build_id()
        if not build_id:
            return {
                "success": False,
                "error": "Could not fetch RailYatri buildId. Using mock data.",
            }

        try:
            # RailYatri PNR API endpoint pattern
            url = f"{RAILYATRI_BASE_URL}/_next/data/{build_id}/pnr-status/{pnr}.json"

            resp = requests.get(url, headers=DEFAULT_HEADERS, timeout=API_TIMEOUT)
            resp.raise_for_status()

            data = resp.json()
            page_props = data.get("pageProps", {})
            pnr_data = page_props.get("pnrStatusData", {})

            # Check if pnrStatusData exists
            if not pnr_data:
                return {
                    "success": False,
                    "error": "PNR data not available . PNR may be old/invalid or not yet generated.",
                }

            if not pnr_data.get("success"):
                error_msg = pnr_data.get("message") or "PNR not found"
                return {"success": False, "error": error_msg}

            # Extract train information
            train_number = pnr_data.get("train_number", "")
            train_name = pnr_data.get("train_name", "")

            if not train_number:
                return {
                    "success": False,
                    "error": "Train number not found in PNR data",
                }

            passengers = pnr_data.get("passengers", [])

            return {
                "success": True,
                "data": {
                    "pnrNumber": pnr,
                    "trainNo": train_number,
                    "trainName": train_name,
                    "fromStn": pnr_data.get("from_station_code", ""),
                    "toStn": pnr_data.get("to_station_code", ""),
                    "journeyDate": pnr_data.get("doj", ""),
                    "journeyClass": pnr_data.get("journey_class", ""),
                    "chartStatus": pnr_data.get("chart_status", ""),
                    "passengers": [
                        {
                            "number": p.get("serial", i + 1),
                            "bookingStatus": p.get("booking_status", ""),
                            "currentStatus": p.get("current_status", ""),
                        }
                        for i, p in enumerate(passengers)
                    ],
                },
            }

        except requests.RequestException as e:
            self._reset_build_id_cache()
            return {
                "success": False,
                "error": f"API request failed: {str(e)}",
            }
        except (KeyError, ValueError) as e:
            return {
                "success": False,
                "error": f"Failed to parse PNR data: {str(e)}",
            }

    def get_pnr_status_mock(self, pnr: str) -> Dict[str, Any]:
        """
        Mock PNR status for development and demo.
        Demo PNRs: 1234567890 (Train 12951), 2234567890 (Train 12301)
        """
        if not self._validate_pnr(pnr):
            return {
                "success": False,
                "error": "Invalid PNR number. Must be 10 digits.",
            }

        # Use different trains based on first digit for variety
        train_mapping = {
            "1": ("12951", "Mumbai Rajdhani Express", "MMCT", "NDLS"),
            "2": ("12301", "Howrah Rajdhani Express", "HWH", "NDLS"),
            "3": ("12446", "Uttar Sampark Kranti Express", "SVDK", "NDLS"),
            "4": ("12627", "Karnataka Express", "SBC", "NDLS"),
            "5": ("12621", "Tamil Nadu Express", "MAS", "NDLS"),
        }

        first_digit = pnr[0]
        train_no, train_name, from_stn, to_stn = train_mapping.get(
            first_digit, train_mapping["1"]
        )

        return {
            "success": True,
            "data": {
                "pnrNumber": pnr,
                "trainNo": train_no,
                "trainName": train_name,
                "fromStn": from_stn,
                "toStn": to_stn,
                "journeyDate": "2026-07-15",
                "journeyClass": "SL",
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

    def get_pnr_status(self, pnr: str, use_api: bool = True) -> Dict[str, Any]:
        """
        Main method to get PNR status.
        Falls back to mock data if API fails.

        Note: RailYatri API may not work for:
        - Old PNRs (journey completed)
        - Very recent PNRs (not yet in system)
        - Cancelled bookings

        For testing, use demo PNRs:
        - 1234567890 (Train 12951 - Mumbai Rajdhani)
        - 2234567890 (Train 12301 - Howrah Rajdhani)
        """
        if use_api:
            result = self.get_pnr_status_from_api(pnr)
            if result["success"]:
                return result
            error_msg = result.get("error", "Unknown error")
            print(f"PNR API failed for {pnr}: {error_msg}, falling back to mock")

        return self.get_pnr_status_mock(pnr)

    @staticmethod
    def _validate_pnr(pnr: str) -> bool:
        """Validate PNR format"""
        return len(pnr) == 10 and pnr.isdigit()

    @staticmethod
    def extract_train_info(pnr_response: Dict[str, Any]) -> Optional[Dict[str, str]]:
        """
        Extract train number and name from PNR response.
        Returns None if data is invalid.
        """
        if not pnr_response.get("success"):
            return None

        data = pnr_response.get("data", {})
        train_no = data.get("trainNo", "")
        train_name = data.get("trainName", "")

        if not train_no:
            return None

        return {"trainNo": train_no, "trainName": train_name}
