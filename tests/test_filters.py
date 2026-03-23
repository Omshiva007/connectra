"""Unit tests for connectra_core/filters.py"""

import pytest

from connectra_core.filters import is_internal_email

INTERNAL_DOMAIN = "mycompany.com"


class TestIsInternalEmail:

    # ------------------------------------------------------------------
    # Edge-case inputs
    # ------------------------------------------------------------------

    def test_empty_string_is_internal(self):
        assert is_internal_email("", INTERNAL_DOMAIN) is True

    def test_none_is_internal(self):
        assert is_internal_email(None, INTERNAL_DOMAIN) is True

    def test_malformed_no_at_sign(self):
        assert is_internal_email("notanemail", INTERNAL_DOMAIN) is True

    # ------------------------------------------------------------------
    # Same company domain → internal
    # ------------------------------------------------------------------

    def test_same_domain_is_internal(self):
        assert is_internal_email("alice@mycompany.com", INTERNAL_DOMAIN) is True

    def test_same_domain_case_insensitive(self):
        assert is_internal_email("BOB@MYCOMPANY.COM", INTERNAL_DOMAIN) is True

    # ------------------------------------------------------------------
    # External domains → not internal
    # ------------------------------------------------------------------

    def test_external_domain_is_not_internal(self):
        assert is_internal_email("client@acme.com", INTERNAL_DOMAIN) is False

    def test_subdomain_of_different_company_is_not_internal(self):
        assert is_internal_email("contact@mail.acme.com", INTERNAL_DOMAIN) is False

    # ------------------------------------------------------------------
    # Always-internal domains
    # ------------------------------------------------------------------

    def test_zoom_us_is_internal(self):
        assert is_internal_email("meeting@zoom.us", INTERNAL_DOMAIN) is True

    def test_otter_ai_is_internal(self):
        assert is_internal_email("notes@otter.ai", INTERNAL_DOMAIN) is True

    def test_fireflies_ai_is_internal(self):
        assert is_internal_email("bot@fireflies.ai", INTERNAL_DOMAIN) is True

    def test_lovable_dev_is_internal(self):
        assert is_internal_email("app@lovable.dev", INTERNAL_DOMAIN) is True

    def test_fathom_video_is_internal(self):
        assert is_internal_email("rec@fathom.video", INTERNAL_DOMAIN) is True

    # ------------------------------------------------------------------
    # Always-internal suffixes
    # ------------------------------------------------------------------

    def test_fieldglass_suffix_is_internal(self):
        assert is_internal_email("vendor@something.fieldglass.cloud.sap", INTERNAL_DOMAIN) is True

    def test_atlassian_net_suffix_is_internal(self):
        assert is_internal_email("jira@tenant.atlassian.net", INTERNAL_DOMAIN) is True

    # ------------------------------------------------------------------
    # Special override – abhijit.roy treated as external
    # ------------------------------------------------------------------

    def test_abhijit_roy_is_always_external(self):
        assert is_internal_email("abhijit.roy@unifiedinfotech.net", INTERNAL_DOMAIN) is False

    # ------------------------------------------------------------------
    # Boundary: email whose local-part contains @-like characters in name
    # ------------------------------------------------------------------

    def test_email_with_plus_addressing(self):
        # plus-addressing on external domain → not internal
        assert is_internal_email("user+tag@external.com", INTERNAL_DOMAIN) is False

    def test_email_with_plus_addressing_internal(self):
        assert is_internal_email("user+tag@mycompany.com", INTERNAL_DOMAIN) is True
