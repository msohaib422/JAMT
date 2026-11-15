"""Phase 2 — Official NASA documents, NTRS/PDS clients, cache and AI grounding.

Live network calls are only executed when JAMT_LIVE_TESTS=1 is set; otherwise
they are skipped. Everything else runs offline against the bundled real corpus.
"""

import json
import os
from types import SimpleNamespace

import pytest

from app.ai import agent, rag
from app.nasa import ntrs, pds
from app.nasa.client import NasaApiUnavailable, get_json
from app.nasa import cache as nasa_cache

MANIFEST_PATH = rag.DATA_PATH.with_name("nasa_documents.json")
LIVE = os.getenv("JAMT_LIVE_TESTS", "0") == "1"


def load_manifest():
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))["documents"]


def load_dataset():
    return json.loads(rag.DATA_PATH.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# 1. Corpus provenance
# ---------------------------------------------------------------------------

class TestCorpusProvenance:
    def test_manifest_covers_required_themes(self):
        topics = set()
        for doc in load_manifest():
            topics |= set(doc.get("topics", []))
        for required in ["moon", "mars", "life_support", "water", "food", "radiation", "astronaut_health", "habitat", "mission_operations", "mission_engineering", "emergency"]:
            assert required in topics, f"missing topic {required}"

    def test_manifest_is_all_public_nasa(self):
        for doc in load_manifest():
            assert doc["distribution"] == "PUBLIC"
            assert doc["ntrs_id"].isdigit()
            assert doc["ntrs_url"].startswith("https://ntrs.nasa.gov/citations/")
            assert doc["fulltext_url"].startswith("https://ntrs.nasa.gov/api/citations/")
            assert doc["category"]

    def test_dataset_has_full_provenance(self):
        dataset = load_dataset()
        assert dataset["documents_indexed"] == len(load_manifest())
        chunks = dataset["chunks"]
        assert chunks
        ids = [c["id"] for c in chunks]
        assert len(ids) == len(set(ids))
        for chunk in chunks:
            assert chunk["distribution"] == "PUBLIC"
            assert chunk["ntrs_id"].isdigit()
            assert chunk["url"].startswith("https://ntrs.nasa.gov/citations/")
            assert chunk["title"]
            assert chunk["content"].strip()
            assert chunk["topics"]
            assert chunk["category"]

    def test_original_excerpts_are_indexed(self):
        dataset = load_dataset()
        text = "\n".join(chunk["content"] for chunk in dataset["chunks"])
        # Verbatim phrases that only exist inside the original NASA publications
        for phrase in [
            "Life Support Baseline Values and Assumptions",   # NASA/TP-2015-218570/REV2
            "galactic cosmic rays",                           # GCR radiation report
            "physiological deconditioning",                    # exercise SP (2025)
            "Design Reference Architecture",                   # NASA/SP-2009-566(-ADD2)
        ]:
            assert phrase.lower() in text.lower(), phrase

    def test_old_unverified_content_is_gone(self):
        dataset = load_dataset()
        text = "\n".join(chunk["content"] for chunk in dataset["chunks"]).lower()
        # Verbatim fragments of the removed developer-written paraphrase dataset
        for forbidden in [
            "lunar vacuum for human spaceflight",
            "focused mission-planning concern",
            "south-pole operations for human spaceflight",
            "battery state-of-charge for human spaceflight",
            "the practical lesson is to pair this design concern",
            "nasa artemis presents the moon as a scientifically valuable destination",
        ]:
            assert forbidden not in text


# ---------------------------------------------------------------------------
# 2. Retrieval
# ---------------------------------------------------------------------------

class TestRetrieval:
    def test_radiation_question_finds_real_radiation_report(self):
        results = rag.search_nasa_knowledge("What does NASA research say about radiation exposure?", top_k=4)
        assert any(r["ntrs_id"] == "20080029284" for r in results)
        assert all(r["score"] >= rag.MIN_RELEVANCE for r in results)

    def test_mars_mission_question_returns_mars_docs(self):
        results = rag.search_nasa_knowledge("Tell me about NASA Mars exploration architecture", top_k=4)
        ids = {r["ntrs_id"] for r in results}
        assert ids & {"20100028285", "20160003093", "20160011571"}

    def test_category_filter(self):
        results = rag.search_nasa_knowledge("oxygen consumption humans", top_k=4, category="life_support")
        assert all(r["category"] == "life_support" for r in results)

    def test_lunar_dust_is_retrievable(self):
        results = rag.search_nasa_knowledge("lunar dust contamination", top_k=4)
        assert any(r["ntrs_id"] == "20230003126" for r in results)

    def test_no_evidence_for_meaningless_query(self):
        assert rag.search_nasa_knowledge("zzqwxv bfuytre mkjgtd", top_k=4) == []

    def test_results_carry_page_and_document_metadata(self):
        results = rag.search_nasa_knowledge("life support water oxygen", top_k=4)
        assert results
        assert all("page" in r for r in results)


# ---------------------------------------------------------------------------
# 3. AI Mission Control grounding
# ---------------------------------------------------------------------------

class TestAgentGrounding:
    def _run(self, message):
        return agent.run_agent(None, message)

    def test_agent_returns_real_nasa_sources(self):
        result = self._run("How do astronauts handle solar radiation storms?")
        assert result["sources"], "expected at least one cited source"
        for source in result["sources"]:
            assert source["title"]
            assert (source.get("link") or "").startswith("https://ntrs.nasa.gov/citations/")

    def test_agent_cannot_verify_unknown_topic(self):
        result = self._run("zzqwxv bfuytre mkjgtd qlorpidx plukesnal")
        assert "currently indexed official NASA documents" in result["response"]
        assert result["sources"] == []

    def test_tools_used_reports_search(self):
        result = self._run("What does NASA say about radiation exposure?")
        assert any(t["label"] == "search_nasa_knowledge" for t in result["tools_used"])


# ---------------------------------------------------------------------------
# 4. Client behaviour (mocked HTTP)
# ---------------------------------------------------------------------------


def _ntrs_payload():
    return {
        "stats": {"total": 2, "maxScore": 200.0},
        "results": [
            {
                "id": 20210024855,
                "title": "Life Support Baseline Values and Assumptions Document",
                "distribution": "PUBLIC",
                "stiTypeDetails": "Technical Publication (TP)",
                "publications": [{"publicationDate": "2022-02-01T00:00:00.0000000+00:00"}],
                "center": {"name": "Johnson Space Center"},
                "abstract": "Baseline values and assumptions for life support.",
                "downloads": [{"links": {"original": "https://ntrs.nasa.gov/api/citations/20210024855/downloads/BVAD_2.15.22-final.pdf"}}],
            },
        ],
    }


def _pds_payload():
    return {
        "summary": {"hits": 2, "properties": ["lid"]},
        "data": [
            {
                "id": "urn:nasa:pds:mars2020_mastcamz_ops_raw::13.0",
                "title": "Mars 2020 Mastcam-Z Operations Raw Product Bundle",
                "targets": [{"id": "urn:nasa:pds:context:target:planet.mars"}],
                "investigations": [{"id": "urn:nasa:pds:context:investigation:mission.mars2020"}],
                "properties": {
                    "ops:Harvest_Info.ops:node_name": ["PDS_IMG"],
                    "ops:Harvest_Info.ops:harvest_date_time": ["2025-04-25T22:28:24.411349Z"],
                },
            },
            {
                "id": "urn:nasa:pds:cas_svr_a::1.0",
                "title": "Apollo 12 ALSEP ARCSAV Solar Wind Spectrometer Raw Cleaned ASCII Data Bundle",
                "targets": [{"id": "urn:nasa:pds:context:target:satellite.earth.moon"}],
                "investigations": [{"id": "urn:nasa:pds:context:investigation:mission.apollo_12"}],
                "properties": {
                    "ops:Harvest_Info.ops:node_name": ["PDS_GEO"],
                    "ops:Harvest_Info.ops:harvest_date_time": ["2026-08-18T03:20:54.205640120Z"],
                },
            },
        ],
    }


class TestNtrsClient:
    def test_search_maps_fields(self, monkeypatch):
        monkeypatch.setattr(ntrs, "get_json", lambda url, params=None: _ntrs_payload())
        monkeypatch.setattr(ntrs, "cache", _NullCache())
        result = ntrs.search_documents("Baseline Values", 5)
        assert result["available"] is True
        assert result["hits"] == 2
        item = result["results"][0]
        assert item["ntrs_id"] == "20210024855"
        assert item["url"] == "https://ntrs.nasa.gov/citations/20210024855"
        assert item["publication_date"] == "2022-02-01"
        assert item["distribution"] == "PUBLIC"

    def test_search_without_results(self, monkeypatch):
        monkeypatch.setattr(ntrs, "get_json", lambda url, params=None: {"stats": {"total": 0}, "results": []})
        monkeypatch.setattr(ntrs, "cache", _NullCache())
        result = ntrs.search_documents("nothing at all qzwxv", 5)
        assert result["available"] is True
        assert result["results"] == []

    def test_malformed_payload_raises(self, monkeypatch):
        monkeypatch.setattr(ntrs, "get_json", lambda url, params=None: [1, 2, 3])
        monkeypatch.setattr(ntrs, "cache", _NullCache())
        with pytest.raises(NasaApiUnavailable):
            ntrs.search_documents("anything", 5)

    def test_unavailable_without_cache(self, monkeypatch):
        monkeypatch.setattr(ntrs, "get_json", lambda url, params=None: (_ for _ in ()).throw(NasaApiUnavailable("network down")))
        monkeypatch.setattr(ntrs, "cache", _NullCache())
        with pytest.raises(NasaApiUnavailable):
            ntrs.search_documents("anything", 5)


class TestPdsClient:
    def test_moon_and_mars_filter_by_target(self, monkeypatch):
        monkeypatch.setattr(pds, "get_json", lambda url, params=None, timeout=None: _pds_payload())
        monkeypatch.setattr(pds, "cache", _NullCache())
        moon = pds.destination_datasets("moon")
        mars = pds.destination_datasets("mars")
        assert all(any("satellite.earth.moon" in t for t in item["target_ids"]) for item in moon["results"])
        assert all(any("planet.mars" in t for t in item["target_ids"]) for item in mars["results"])
        assert moon["results"][0]["title"].startswith("Apollo")
        assert mars["results"][0]["title"].startswith("Mars")

    def test_unsupported_destination(self, monkeypatch):
        monkeypatch.setattr(pds, "get_json", lambda url, params=None, timeout=None: _pds_payload())
        with pytest.raises(NasaApiUnavailable):
            pds.destination_datasets("jupiter")

    def test_unavailable_without_cache(self, monkeypatch):
        monkeypatch.setattr(pds, "get_json", lambda url, params=None, timeout=None: (_ for _ in ()).throw(NasaApiUnavailable("network down")))
        monkeypatch.setattr(pds, "cache", _NullCache())
        with pytest.raises(NasaApiUnavailable):
            pds.destination_datasets("moon")


class _NullCache:
    def read(self, namespace, params):
        return None

    def write(self, namespace, params, payload):
        return None


# ---------------------------------------------------------------------------
# 5. Cache behaviour
# ---------------------------------------------------------------------------

class TestCache:
    def test_roundtrip(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            nasa_cache,
            "_cache_root",
            lambda: tmp_path / "nasa",
        )
        from app.ai.config import get_config
        cfg = dict(get_config())
        cfg["nasa_data_cache_ttl"] = 3600
        monkeypatch.setattr(nasa_cache, "get_config", lambda: cfg)
        nasa_cache.write("test_namespace", {"a": 1}, {"hello": "world"})
        cached = nasa_cache.read("test_namespace", {"a": 1})
        assert cached and cached["payload"] == {"hello": "world"}
        assert cached["fresh"] is True

    def test_expired_is_not_fresh(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            nasa_cache,
            "_cache_root",
            lambda: tmp_path / "nasa",
        )
        from app.ai.config import get_config
        cfg = dict(get_config())
        cfg["nasa_data_cache_ttl"] = 0
        monkeypatch.setattr(nasa_cache, "get_config", lambda: cfg)
        nasa_cache.write("test_namespace", {"a": 1}, {"hello": "world"})
        cached = nasa_cache.read("test_namespace", {"a": 1})
        assert cached and cached["fresh"] is False


# ---------------------------------------------------------------------------
# 6. API endpoints
# ---------------------------------------------------------------------------

class TestNasaEndpoints:
    def test_sources_lists_real_publications(self, ac):
        response = ac.get("/api/nasa/sources")
        assert response.status_code == 200
        payload = response.json()
        assert payload["available"] is True
        assert payload["total_documents"] == len(load_manifest())
        ids = {doc["ntrs_id"] for doc in payload["documents"]}
        assert "20210024855" in ids

    def test_status(self, ac):
        response = ac.get("/api/nasa/status")
        assert response.status_code == 200
        payload = response.json()
        assert payload["enabled"] is True
        assert payload["knowledge_documents_indexed"] == len(load_manifest())
        assert payload["knowledge_chunks_indexed"] > 0

    def test_datasets_flag_off(self, ac, monkeypatch):
        from app.ai.config import get_config
        cfg = dict(get_config())
        cfg["nasa_data_enabled"] = False
        monkeypatch.setattr("app.main.get_config", lambda: cfg)
        response = ac.get("/api/nasa/datasets", params={"destination": "mars"})
        payload = response.json()
        assert payload["available"] is False
        assert payload["enabled"] is False

    def test_reports_flag_off(self, ac, monkeypatch):
        from app.ai.config import get_config
        cfg = dict(get_config())
        cfg["nasa_data_enabled"] = False
        monkeypatch.setattr("app.main.get_config", lambda: cfg)
        response = ac.get("/api/nasa/reports", params={"q": "radiation"})
        assert response.json()["available"] is False

    def test_reports_null_source_when_down(self, ac, monkeypatch):
        monkeypatch.setattr(
            "app.main.search_documents",
            lambda q, limit: (_ for _ in ()).throw(NasaApiUnavailable("down for tests")),
        )
        response = ac.get("/api/nasa/reports", params={"q": "radiation"})
        payload = response.json()
        assert payload["available"] is False
        assert "radiation" in payload["query"]

    def test_datasets_offline_failure_returns_message_not_fake(self, ac, monkeypatch):
        monkeypatch.setattr(
            "app.main.destination_datasets",
            lambda destination, limit: (_ for _ in ()).throw(NasaApiUnavailable("down for tests")),
        )
        response = ac.get("/api/nasa/datasets", params={"destination": "mars"})
        payload = response.json()
        assert payload["available"] is False
        assert "results" not in payload


# ---------------------------------------------------------------------------
# 7. Live connectivity — skipped unless explicitly enabled
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not LIVE, reason="live NASA connectivity tests opt-in via JAMT_LIVE_TESTS=1")
class TestLiveConnectivity:
    def test_ntrs_reports_reachable(self):
        result = ntrs.search_documents("Baseline Values and Assumptions", 3)
        assert result["available"] is True
        assert result["results"]

    def test_pds_bundles_reachable(self):
        result = pds.destination_datasets("mars", 3)
        assert result["available"] is True
        assert result["matching_bundles"] > 0
