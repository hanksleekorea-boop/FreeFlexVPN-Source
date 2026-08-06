#!/usr/bin/env python3
"""신규 공급자 원가 입력의 통화·약관·속도 계약 검사."""
from __future__ import annotations

import pathlib
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "20_SRC"))

import cost_model  # noqa: E402


def base_spec():
    return {
        "provider_id": "example_cloud",
        "plan_id": "vpn_1",
        "countries": ["JP"],
        "checked_on": "2026-08-03",
        "source_url": "https://example.com/pricing",
        "grade": "안전",
        "vpn_resale_status": "allowed",
        "port_mbps": 1000,
        "commitment_months": 1,
        "pricing": {
            "components": [
                {"label": "base", "currency": "eur", "amount": 4.5, "cadence": "monthly"},
                {"label": "region", "currency": "usd", "amount": 1.16, "cadence": "monthly"},
            ],
            "traffic": {
                "model": "included_tb", "included_tb": 1,
                "overage": {"currency": "usd", "amount_per_tb": 10},
            },
        },
    }


class CostProviderContractTests(unittest.TestCase):
    def test_mixed_currency_is_converted_component_by_component(self):
        result = cost_model.validate_provider_input(base_spec())
        expected = 4.5 * cost_model.FX["eur"] + 1.16 * cost_model.FX["usd"]
        self.assertTrue(result["mixed_currency"])
        self.assertEqual(result["monthly_base_krw"], expected)
        self.assertEqual(result["traffic"]["overage"]["krw_per_tb"], 10 * cost_model.FX["usd"])

    def test_input_is_not_automatically_added_to_country_options(self):
        result = cost_model.validate_provider_input(base_spec())
        self.assertEqual(result["admission"], "validated_input_only_not_added_to_country_options")
        self.assertNotIn("example_cloud", repr(cost_model.COUNTRY_OPTIONS))

    def test_unknown_currency_is_rejected(self):
        value = base_spec()
        value["pricing"]["components"][0]["currency"] = "krw"
        with self.assertRaises(ValueError):
            cost_model.validate_provider_input(value)

    def test_price_components_must_be_monthly(self):
        value = base_spec()
        value["pricing"]["components"][0]["cadence"] = "yearly"
        with self.assertRaises(ValueError):
            cost_model.validate_provider_input(value)

    def test_https_source_cannot_contain_credentials_or_tracking_query(self):
        credential_url = "https://" + "user" + ":" + "credential" + "@" + "example.com/pricing"
        for url in ("http://example.com/pricing", credential_url, "https://example.com/pricing?ref=x"):
            value = base_spec()
            value["source_url"] = url
            with self.subTest(url=url), self.assertRaises(ValueError):
                cost_model.validate_provider_input(value)

    def test_unmetered_requires_fair_use_and_speed_cap(self):
        value = base_spec()
        value["pricing"]["traffic"] = {"model": "unmetered"}
        with self.assertRaises(ValueError):
            cost_model.validate_provider_input(value)
        value["grade"] = "공격"
        value["pricing"]["traffic"] = {"model": "unmetered", "fair_use_status": "unknown", "speed_cap_mbps": 80}
        result = cost_model.validate_provider_input(value)
        self.assertEqual(result["traffic"]["speed_cap_mbps"], 80)

    def test_unknown_fair_use_cannot_be_safe(self):
        value = base_spec()
        value["pricing"]["traffic"] = {"model": "unmetered", "fair_use_status": "unknown", "speed_cap_mbps": 100}
        with self.assertRaises(ValueError):
            cost_model.validate_provider_input(value)

    def test_bandwidth_blocks_require_explicit_block_price(self):
        value = base_spec()
        value["pricing"]["traffic"] = {"model": "bandwidth_blocks", "base_mbps": 10, "block_mbps": 10}
        with self.assertRaises(ValueError):
            cost_model.validate_provider_input(value)
        value["pricing"]["traffic"]["block_price"] = {"currency": "usd", "amount": 15}
        result = cost_model.validate_provider_input(value)
        self.assertEqual(result["traffic"]["block_price"]["krw"], 15 * cost_model.FX["usd"])

    def test_unknown_vpn_resale_terms_cannot_be_safe(self):
        value = base_spec()
        value["vpn_resale_status"] = "unknown"
        with self.assertRaises(ValueError):
            cost_model.validate_provider_input(value)

    def test_forbidden_vpn_resale_is_excluded(self):
        value = base_spec()
        value["vpn_resale_status"] = "forbidden"
        value["grade"] = "미확인"
        with self.assertRaises(ValueError):
            cost_model.validate_provider_input(value)

    def test_countries_are_iso_unique_and_checked_date_is_not_future(self):
        for countries in ([], ["Japan"], ["JP", "JP"]):
            value = base_spec()
            value["countries"] = countries
            with self.subTest(countries=countries), self.assertRaises(ValueError):
                cost_model.validate_provider_input(value)
        value = base_spec()
        value["checked_on"] = "2999-01-01"
        with self.assertRaises(ValueError):
            cost_model.validate_provider_input(value)


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(CostProviderContractTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    total = result.testsRun
    passed = total - len(result.failures) - len(result.errors)
    print(f"공급자 원가 입력 계약 검사 {passed}/{total} 통과")
    raise SystemExit(0 if result.wasSuccessful() else 1)
