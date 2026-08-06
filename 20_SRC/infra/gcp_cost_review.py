#!/usr/bin/env python3
"""GCP 첫 노드의 확인 가능한 월비용 하한을 재현 가능하게 계산한다."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


FREE_TIER_REGIONS = ("us-west1", "us-central1", "us-east1")
DESTINATION_RATES_USD_PER_GIB = {
    "north_america": 0.12,
    "europe": 0.12,
    "asia_excluding_korea_indonesia": 0.12,
    "korea": 0.19,
    "indonesia": 0.19,
    "australia": 0.19,
    "south_america": 0.19,
    "saudi_arabia": 0.19,
    "middle_east_excluding_saudi": 0.15,
    "africa": 0.15,
    "china_excluding_hong_kong": 0.23,
}
FREE_TIER_EGRESS_EXCLUDED = ("australia", "china_excluding_hong_kong")


@dataclass(frozen=True)
class GCPPriceSnapshot:
    as_of: str = "2026-08-03"
    external_ipv4_usd_per_hour: float = 0.005
    free_tier_egress_gib: float = 1.0
    free_tier_disk_gib_month: float = 30.0
    illustrative_krw_per_usd: float = 1470.0


def _money(value: float) -> float:
    return round(value + 1e-12, 2)


def estimate_first_node_month(
    *,
    usage_gib: float,
    destination: str,
    hours: float = 730.0,
    region: str = "us-west1",
    disk_gib: float = 10.0,
    free_tier_eligible: bool = True,
    prices: GCPPriceSnapshot | None = None,
) -> dict[str, Any]:
    """Compute a conservative known-cost floor; unknown VM cost is never guessed."""
    prices = prices or GCPPriceSnapshot()
    if usage_gib < 0:
        raise ValueError("usage_gib must be >= 0")
    if not 0 <= hours <= 744:
        raise ValueError("hours must be between 0 and 744")
    if disk_gib <= 0:
        raise ValueError("disk_gib must be > 0")
    if destination not in DESTINATION_RATES_USD_PER_GIB:
        raise ValueError(f"unsupported destination: {destination}")

    region_eligible = region in FREE_TIER_REGIONS
    effective_free_tier = free_tier_eligible and region_eligible
    free_egress = 0.0
    if effective_free_tier and destination not in FREE_TIER_EGRESS_EXCLUDED:
        free_egress = prices.free_tier_egress_gib

    billed_gib = max(usage_gib - free_egress, 0.0)
    egress_usd = billed_gib * DESTINATION_RATES_USD_PER_GIB[destination]
    ipv4_usd = hours * prices.external_ipv4_usd_per_hour
    disk_is_covered = effective_free_tier and disk_gib <= prices.free_tier_disk_gib_month
    known_minimum_usd = ipv4_usd + egress_usd
    unknown_costs: list[str] = []
    if not effective_free_tier:
        unknown_costs.append("e2-micro compute SKU price: verify in authenticated console")
    if not disk_is_covered:
        unknown_costs.append("pd-standard disk overage: verify in authenticated console")

    return {
        "usage_gib": round(usage_gib, 3),
        "destination": destination,
        "region": region,
        "hours": round(hours, 2),
        "free_tier_assumed": effective_free_tier,
        "free_egress_gib_assumed": free_egress,
        "billed_egress_gib": round(billed_gib, 3),
        "external_ipv4_usd": _money(ipv4_usd),
        "egress_usd": _money(egress_usd),
        "known_minimum_usd": _money(known_minimum_usd),
        "illustrative_known_minimum_krw": round(known_minimum_usd * prices.illustrative_krw_per_usd),
        "compute": "FREE_TIER_ASSUMED" if effective_free_tier else "UNKNOWN_VERIFY_CONSOLE",
        "disk": "FREE_TIER_ASSUMED" if disk_is_covered else "UNKNOWN_VERIFY_CONSOLE",
        "unknown_costs": unknown_costs,
    }


def build_cost_review(
    *,
    destination: str = "korea",
    usages_gib: tuple[float, ...] = (1.0, 10.0, 100.0),
    hours: float = 730.0,
) -> dict[str, Any]:
    prices = GCPPriceSnapshot()
    scenarios = [
        estimate_first_node_month(
            usage_gib=usage,
            destination=destination,
            hours=hours,
            prices=prices,
        )
        for usage in usages_gib
    ]
    return {
        "schema": "FreeFlexVPNGCPCostReviewV1",
        "candidate": "v2.12-gcp-cost-review",
        "price_snapshot_date": prices.as_of,
        "assumptions": {
            "machine_type": "e2-micro",
            "region": "us-west1",
            "disk_gib": 10,
            "network_tier": "Premium",
            "monthly_hours": hours,
            "free_tier_eligibility": "ASSUMED_FOR_ESTIMATE_VERIFY_IN_AUTHENTICATED_CONSOLE",
            "illustrative_krw_per_usd": prices.illustrative_krw_per_usd,
        },
        "official_sources": {
            "free_tier": "https://docs.cloud.google.com/free/docs/free-cloud-features",
            "vpc_pricing": "https://cloud.google.com/vpc/pricing",
            "compute_pricing": "https://cloud.google.com/products/compute/pricing",
        },
        "scenarios": scenarios,
        "console_checks_before_create": [
            "billing account is active and the project is attached to it",
            "e2-micro Free Tier eligibility is shown for the selected US region",
            "Welcome credit amount and expiry, if any, are recorded",
            "external IPv4 hourly charge is included",
            "Premium Tier egress destination and expected GiB are included",
            "budget alert is configured and understood not to be a hard spend cap",
        ],
        "decision": "DO_NOT_CREATE_UNTIL_AUTHENTICATED_CONSOLE_READBACK",
        "evidence_level": "official public pricing readback plus local deterministic calculation; no authenticated billing, cloud, server, device, or user evidence",
        "contains_secrets": False,
    }
