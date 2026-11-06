"""Pipeline stage runner - single entry point for stage execution.

Wraps the multi-agent worker fleet into named, replayable stages consumed by
api.py (`POST /api/pipeline/run`) and main.py.
"""
from __future__ import annotations

import sys

from agents import (
    DiscoveryAgent,
    WebIntelAgent,
    QualificationAgent,
    EnrichmentAgent,
    PitchAgent,
)
from logger import log


STAGES = ("scrape", "qualify", "enrich", "draft", "send")


def run_stage(stage: str, limit: int | None = None) -> dict:
    """Execute one pipeline stage synchronously; returns a summary dict.

    `scrape` runs discovery + web intel; `send` runs the Gmail engine;
    everything else maps 1:1 to a worker agent.
    """
    if stage not in STAGES and stage != "all":
        raise ValueError(f"Unknown stage '{stage}'. Options: {list(STAGES)} + 'all'")

    results: dict = {}
    if stage == "scrape":
        results["discovery"] = DiscoveryAgent(limit=limit or 40).run()
        results["web_intel"] = WebIntelAgent(limit=limit).run()
    elif stage == "qualify":
        results["qualified"] = QualificationAgent().run(limit=limit)
    elif stage == "enrich":
        results["enriched"] = EnrichmentAgent().run(limit=limit)
    elif stage == "draft":
        results["drafted"] = PitchAgent().run(limit=limit)
    elif stage == "send":
        import send_gmail
        results["sent"] = send_gmail.stage_send(limit or 25)
    elif stage == "all":
        results["discovery"] = DiscoveryAgent().run()
        results["web_intel"] = WebIntelAgent().run()
        results["qualified"] = QualificationAgent().run()
        results["enriched"] = EnrichmentAgent().run()
        results["drafted"] = PitchAgent().run()
        import send_gmail
        results["sent"] = send_gmail.stage_send()

    log.info(f"[runner] stage '{stage}' complete: {results}")
    return results


def main() -> None:
    stage = sys.argv[1] if len(sys.argv) > 1 else "all"
    print(run_stage(stage))


if __name__ == "__main__":
    main()