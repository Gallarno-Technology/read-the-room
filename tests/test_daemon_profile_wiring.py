"""Daemon-level wiring tests for the 3-profile + sentiment ContentChecker build.

_build_content_checker is a pure factory, so these run without the poll harness.
Verifies the 3 profiles map to the expected keyword-scanner config and that the
sentiment service/cache + active_profile are threaded onto the ContentChecker.
"""
from unittest.mock import MagicMock

import daemon
from profiles import CLOSE_FRIENDS, FAMILY_FRIENDLY, MIXED_COMPANY


def _scanners():
    return MagicMock(), MagicMock(), MagicMock(), MagicMock()


def test_profile_map_has_exactly_the_three_profiles():
    assert set(daemon.PROFILE_MAP) == {FAMILY_FRIENDLY, MIXED_COMPANY, CLOSE_FRIENDS}


def test_family_friendly_is_strictest():
    lyr, prof, drug, sexual = _scanners()
    cc = daemon._build_content_checker(FAMILY_FRIENDLY, lyr, prof, drug, sexual)
    assert cc.explicit_skip is True
    assert cc.drug_scanner is not None
    assert cc.active_profile == FAMILY_FRIENDLY


def test_close_friends_passes_explicit_flag():
    lyr, prof, drug, sexual = _scanners()
    cc = daemon._build_content_checker(CLOSE_FRIENDS, lyr, prof, drug, sexual)
    assert cc.explicit_skip is False
    assert cc.active_profile == CLOSE_FRIENDS


def test_unknown_profile_falls_back_to_default():
    lyr, prof, drug, sexual = _scanners()
    cc = daemon._build_content_checker("bogus", lyr, prof, drug, sexual)
    assert cc.active_profile == daemon.DEFAULT_PROFILE


def test_sentiment_service_and_cache_are_threaded():
    lyr, prof, drug, sexual = _scanners()
    svc, cache = MagicMock(), MagicMock()
    cc = daemon._build_content_checker(
        MIXED_COMPANY, lyr, prof, drug, sexual,
        track_cache=None, sentiment_service=svc, sentiment_cache=cache,
    )
    assert cc.sentiment_service is svc
    assert cc.sentiment_cache is cache
    assert cc.active_profile == MIXED_COMPANY


def test_sentiment_defaults_to_none_when_not_passed():
    lyr, prof, drug, sexual = _scanners()
    cc = daemon._build_content_checker(FAMILY_FRIENDLY, lyr, prof, drug, sexual)
    assert cc.sentiment_service is None
    assert cc.sentiment_cache is None
