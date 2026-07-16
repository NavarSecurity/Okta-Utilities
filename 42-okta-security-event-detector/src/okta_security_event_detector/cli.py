from __future__ import annotations

import argparse
from pathlib import Path

from .config import load_config
from .detector import detect
from .filters import apply_filters
from .loader import load_events
from .normalize import normalize_event
from .reports import write_detection_outputs, write_dry_run_report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Analyze Okta System Log exports for risky or suspicious activity.")
    parser.add_argument("--config", required=True, help="Path to config JSON file.")
    parser.add_argument("--dry-run", action="store_true", help="Validate inputs and write dry-run evidence without full analysis.")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    config = load_config(args.config)
    input_file = Path(config["inputFile"])

    if args.dry_run:
        input_exists = input_file.exists()
        event_count = None
        if input_exists:
            try:
                event_count = len(load_events(input_file))
            except Exception:
                event_count = None
        out_dir = write_dry_run_report(config, input_exists=input_exists, input_event_count=event_count)
        print(f"Dry-run completed. Output: {out_dir}")
        return

    events = load_events(input_file)
    normalized_events = [normalize_event(event) for event in events]
    filtered_events = apply_filters(normalized_events, config)
    detections = detect(filtered_events, config)
    warnings = []
    if len(filtered_events) == 0:
        warnings.append("No events remained after filters were applied.")
    if len(detections) == 0:
        warnings.append("No security detections were produced for the analyzed event set.")
    out_dir = write_detection_outputs(config, normalized_events, filtered_events, detections, warnings)
    print(f"Security event analysis completed. Output: {out_dir}")
