"""Candidate profile load/update and JSON seed import."""

from src.candidate.profile.service import get_profile, seed_from_json, update_profile

__all__ = ["get_profile", "seed_from_json", "update_profile"]
