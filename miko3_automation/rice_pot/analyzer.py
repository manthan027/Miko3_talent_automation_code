"""
RICE POT Analyzer
=================
Scores and prioritizes Miko3 talent tests using the RICE POT framework.
"""

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class RICEScore:
    """RICE POT score for a single talent."""
    talent_name: str
    reach: int          # 1-10: How many users/scenarios does this cover?
    impact: int         # 1-10: How significant is the quality/time improvement?
    confidence: int     # 1-10: How sure are we the automation works reliably?
    effort: int         # 1-10: Inverted — higher = less effort = better

    @property
    def rice_score(self) -> float:
        """Calculate RICE priority score: (R × I × C) / E"""
        if self.effort == 0:
            return 0
        return (self.reach * self.impact * self.confidence) / self.effort

    @property
    def priority_label(self) -> str:
        """Get human-readable priority label."""
        score = self.rice_score
        if score >= 100:
            return "🔴 CRITICAL"
        elif score >= 60:
            return "🟠 HIGH"
        elif score >= 30:
            return "🟡 MEDIUM"
        else:
            return "🟢 LOW"

    def to_dict(self) -> dict:
        return {
            "talent_name": self.talent_name,
            "reach": self.reach,
            "impact": self.impact,
            "confidence": self.confidence,
            "effort": self.effort,
            "rice_score": round(self.rice_score, 1),
            "priority": self.priority_label,
        }


class RICEPOTAnalyzer:
    """
    RICE POT Framework Analyzer for talent test prioritization.

    The RICE framework helps prioritize which talents to automate first:

    - **Reach**: How many users or test scenarios does this talent cover?
      Higher reach = more value from automation.

    - **Impact**: What is the time saved or quality improvement?
      Higher impact = bigger ROI.

    - **Confidence**: How reliable will the ADB automation be for this talent?
      Some talents have more predictable UIs than others.

    - **Effort**: Time and complexity to create and maintain the automation.
      Inverted scale (higher = less effort = better priority).

    **POT (Prioritization Over Time)**: Considers how priority may shift
    as the talent evolves or as more data is collected.

    Formula: Priority Score = (Reach × Impact × Confidence) / Effort

    Usage:
        analyzer = RICEPOTAnalyzer(config)
        scores = analyzer.analyze_all()
        prioritized = analyzer.get_prioritized_list()
    """

    # Default scores if not in config
    DEFAULT_SCORES = {
        "video": {"reach": 9, "impact": 8, "confidence": 7, "effort": 5},
        "storymaker": {"reach": 7, "impact": 7, "confidence": 6, "effort": 4},
        "storytelling": {"reach": 8, "impact": 8, "confidence": 7, "effort": 6},
        "thirdparty": {"reach": 5, "impact": 6, "confidence": 4, "effort": 3},
    }

    # Detailed justifications for each score
    JUSTIFICATIONS = {
        "video": {
            "reach": "Video is used by most Miko3 users; covers multiple video types",
            "impact": "Automating video saves significant manual testing time (10+ videos)",
            "confidence": "Video playback is predictable; play/next buttons are consistent",
            "effort": "Moderate effort — needs coordinate calibration per device model",
        },
        "storymaker": {
            "reach": "Popular with younger users; moderate usage frequency",
            "impact": "Multi-step creation flow saves manual effort per test cycle",
            "confidence": "UI flow is sequential but may have variable element positions",
            "effort": "Higher effort — multi-step flow with animations and transitions",
        },
        "storytelling": {
            "reach": "Widely used feature; core Miko3 experience",
            "impact": "Session monitoring catches audio/visual issues early",
            "confidence": "Playback is reliable; session detect is straightforward",
            "effort": "Moderate effort — mostly waiting and monitoring, less interaction",
        },
        "thirdparty": {
            "reach": "Varies per talent; depends on user's installed talents",
            "impact": "Catches crash/stability issues before users encounter them",
            "confidence": "Low — unknown UIs; smoke test only, no deep validation",
            "effort": "High effort to customize per talent; generic smoke is easy",
        },
    }

    def __init__(self, config: dict):
        """
        Initialize analyzer with config scores.

        Args:
            config: Full config dict (uses 'rice_pot' section).
        """
        self.config_scores = config.get("rice_pot", {})

    def get_score(self, talent_key: str) -> RICEScore:
        """
        Get the RICE score for a specific talent.

        Args:
            talent_key: Talent identifier (e.g., "video", "storymaker").

        Returns:
            RICEScore dataclass.
        """
        # Use config scores, fall back to defaults
        scores = self.config_scores.get(
            talent_key,
            self.DEFAULT_SCORES.get(talent_key, {
                "reach": 5, "impact": 5, "confidence": 5, "effort": 5
            }),
        )

        display_names = {
            "video": "Video Talent",
            "storymaker": "Storymaker Talent",
            "storytelling": "Storytelling Talent",
            "thirdparty": "Third-Party Talents",
        }

        return RICEScore(
            talent_name=display_names.get(talent_key, talent_key.title()),
            reach=scores.get("reach", 5),
            impact=scores.get("impact", 5),
            confidence=scores.get("confidence", 5),
            effort=scores.get("effort", 5),
        )

    def analyze_all(self) -> List[RICEScore]:
        """
        Analyze all known talents.

        Returns:
            List of RICEScore objects.
        """
        talents = ["video", "storymaker", "storytelling", "thirdparty"]
        scores = [self.get_score(t) for t in talents]
        return scores

    def get_prioritized_list(self) -> List[RICEScore]:
        """
        Get talents sorted by priority score (highest first).

        Returns:
            Sorted list of RICEScore objects.
        """
        scores = self.analyze_all()
        scores.sort(key=lambda s: s.rice_score, reverse=True)
        return scores

    def get_justifications(self, talent_key: str) -> Dict[str, str]:
        """
        Get detailed justifications for a talent's RICE scores.

        Args:
            talent_key: Talent identifier.

        Returns:
            Dict of dimension → justification string.
        """
        return self.JUSTIFICATIONS.get(talent_key, {})

    def generate_summary(self) -> str:
        """
        Generate a formatted text summary of the RICE POT analysis.

        Returns:
            Multi-line formatted string.
        """
        prioritized = self.get_prioritized_list()
        lines = [
            "=" * 70,
            "RICE POT PRIORITIZATION ANALYSIS",
            "=" * 70,
            "",
            f"{'Talent':<25} {'R':>4} {'I':>4} {'C':>4} {'E':>4} {'Score':>8} {'Priority':<15}",
            "-" * 70,
        ]

        for score in prioritized:
            lines.append(
                f"{score.talent_name:<25} "
                f"{score.reach:>4} {score.impact:>4} "
                f"{score.confidence:>4} {score.effort:>4} "
                f"{score.rice_score:>8.1f} {score.priority_label:<15}"
            )

        lines.extend([
            "",
            "-" * 70,
            "Formula: Score = (Reach × Impact × Confidence) / Effort",
            "Scale: 1-10 for each dimension (Effort inverted: higher = less effort)",
            "",
            "RECOMMENDATION:",
        ])

        if prioritized:
            top = prioritized[0]
            lines.append(
                f"  → Automate '{top.talent_name}' first (Score: {top.rice_score:.1f})"
            )
            if len(prioritized) > 1:
                second = prioritized[1]
                lines.append(
                    f"  → Then '{second.talent_name}' (Score: {second.rice_score:.1f})"
                )

        lines.append("=" * 70)
        return "\n".join(lines)

    def to_report_data(self) -> dict:
        """
        Get data formatted for HTML report embedding.

        Returns:
            Dict with scores, prioritized list, and justifications.
        """
        prioritized = self.get_prioritized_list()
        return {
            "scores": [s.to_dict() for s in prioritized],
            "summary": self.generate_summary(),
            "justifications": {
                key: self.get_justifications(key)
                for key in ["video", "storymaker", "storytelling", "thirdparty"]
            },
        }
