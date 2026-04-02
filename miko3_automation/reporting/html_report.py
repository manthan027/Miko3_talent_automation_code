"""
HTML Report Generator
=====================
Generates rich HTML test reports with embedded screenshots,
pass/fail badges, RICE POT analysis, and detailed test results.
"""

import os
import base64
import logging
from datetime import datetime
from typing import List, Optional

from ..rice_pot.analyzer import RICEPOTAnalyzer

logger = logging.getLogger(__name__)


class HTMLReportGenerator:
    """
    Generates professional HTML test reports.

    Features:
    - Executive summary with pass/fail counts
    - Per-talent detail sections with expandable steps
    - Embedded screenshots (base64 encoded)
    - Color-coded status badges
    - RICE POT prioritization table
    - Device info and environment details
    - Dark theme with modern styling
    - Print-friendly layout

    Usage:
        report = HTMLReportGenerator(config)
        report.add_result(test_result)
        report.generate("reports/report.html")
    """

    def __init__(self, config: dict):
        """
        Initialize report generator.

        Args:
            config: Full config dict.
        """
        report_cfg = config.get("reporting", {})
        self.output_dir = report_cfg.get("output_dir", "reports")
        self.embed_screenshots = report_cfg.get("embed_screenshots", True)
        self.max_log_lines = report_cfg.get("max_log_lines", 200)
        self.results = []
        self.config = config
        self.device_info = {}
        self.start_time = datetime.now()

    def add_result(self, result) -> None:
        """Add a TestResult to the report."""
        self.results.append(result)
        if result.device_info and not self.device_info:
            self.device_info = result.device_info

    def set_device_info(self, info: dict) -> None:
        """Set device information for the report header."""
        self.device_info = info

    def _encode_screenshot(self, filepath: str) -> str:
        """Encode a screenshot as base64 for embedding."""
        try:
            if os.path.exists(filepath):
                with open(filepath, "rb") as f:
                    data = base64.b64encode(f.read()).decode("utf-8")
                return f"data:image/png;base64,{data}"
        except Exception as e:
            logger.warning("Could not encode screenshot %s: %s", filepath, e)
        return ""

    def _status_badge(self, status: str) -> str:
        """Generate an HTML status badge."""
        colors = {
            "PASSED": ("#10b981", "#064e3b"),
            "FAILED": ("#ef4444", "#7f1d1d"),
            "ERROR": ("#f59e0b", "#78350f"),
            "SKIPPED": ("#6b7280", "#374151"),
            "RUNNING": ("#3b82f6", "#1e3a5f"),
            "NOT_RUN": ("#9ca3af", "#4b5563"),
        }
        bg, text_bg = colors.get(status, ("#6b7280", "#374151"))
        return (
            f'<span style="background:{bg};color:white;padding:3px 10px;'
            f'border-radius:12px;font-size:12px;font-weight:600;">{status}</span>'
        )

    def generate(self, output_path: str = "") -> str:
        """
        Generate the HTML report.

        Args:
            output_path: Custom output path (default: auto-generated in output_dir).

        Returns:
            Path to the generated report.
        """
        if not output_path:
            os.makedirs(self.output_dir, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = os.path.join(
                self.output_dir, f"miko3_test_report_{timestamp}.html"
            )

        # Calculate summary stats
        total = len(self.results)
        passed = sum(1 for r in self.results if r.status.value == "PASSED")
        failed = sum(1 for r in self.results if r.status.value == "FAILED")
        errors = sum(1 for r in self.results if r.status.value == "ERROR")
        duration = sum(r.duration for r in self.results)

        # RICE POT analysis
        rice_analyzer = RICEPOTAnalyzer(self.config)
        rice_data = rice_analyzer.to_report_data()

        # Build HTML
        html = self._build_html(
            total=total,
            passed=passed,
            failed=failed,
            errors=errors,
            duration=duration,
            rice_data=rice_data,
        )

        # Write file
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html)

        logger.info("Report generated: %s", output_path)
        return output_path

    def _build_html(self, total, passed, failed, errors, duration, rice_data) -> str:
        """Build the complete HTML document."""
        now = datetime.now()

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Miko3 Talents Test Report — {now.strftime('%Y-%m-%d %H:%M')}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
            background: #0f172a;
            color: #e2e8f0;
            line-height: 1.6;
            padding: 20px;
        }}
        .container {{ max-width: 1200px; margin: 0 auto; }}

        /* Header */
        .header {{
            background: linear-gradient(135deg, #1e293b, #334155);
            border-radius: 16px;
            padding: 32px;
            margin-bottom: 24px;
            border: 1px solid #475569;
        }}
        .header h1 {{
            font-size: 28px;
            background: linear-gradient(to right, #60a5fa, #a78bfa);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 8px;
        }}
        .header .meta {{ color: #94a3b8; font-size: 14px; }}

        /* Summary Cards */
        .summary-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 16px;
            margin-bottom: 24px;
        }}
        .card {{
            background: #1e293b;
            border-radius: 12px;
            padding: 20px;
            text-align: center;
            border: 1px solid #334155;
            transition: transform 0.2s;
        }}
        .card:hover {{ transform: translateY(-2px); }}
        .card .value {{
            font-size: 36px;
            font-weight: 700;
            margin: 8px 0;
        }}
        .card .label {{ color: #94a3b8; font-size: 13px; text-transform: uppercase; }}
        .card.pass .value {{ color: #10b981; }}
        .card.fail .value {{ color: #ef4444; }}
        .card.error .value {{ color: #f59e0b; }}
        .card.total .value {{ color: #60a5fa; }}
        .card.time .value {{ color: #a78bfa; font-size: 24px; }}

        /* Progress Bar */
        .progress-bar {{
            background: #334155;
            border-radius: 8px;
            height: 12px;
            overflow: hidden;
            margin-bottom: 24px;
        }}
        .progress-fill {{
            height: 100%;
            border-radius: 8px;
            transition: width 0.5s ease;
        }}

        /* Device Info */
        .device-info {{
            background: #1e293b;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 24px;
            border: 1px solid #334155;
        }}
        .device-info h3 {{ color: #60a5fa; margin-bottom: 12px; }}
        .device-info table {{ width: 100%; }}
        .device-info td {{ padding: 4px 12px; }}
        .device-info td:first-child {{ color: #94a3b8; width: 160px; }}

        /* Section */
        .section {{
            background: #1e293b;
            border-radius: 12px;
            margin-bottom: 16px;
            border: 1px solid #334155;
            overflow: hidden;
        }}
        .section-header {{
            padding: 16px 20px;
            cursor: pointer;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid #334155;
        }}
        .section-header:hover {{ background: #243048; }}
        .section-header h3 {{ font-size: 16px; }}
        .section-body {{ padding: 20px; display: none; }}
        .section.open .section-body {{ display: block; }}

        /* Steps Table */
        .steps-table {{ width: 100%; border-collapse: collapse; margin: 12px 0; }}
        .steps-table th {{
            background: #334155;
            padding: 8px 12px;
            text-align: left;
            font-size: 12px;
            text-transform: uppercase;
            color: #94a3b8;
        }}
        .steps-table td {{ padding: 8px 12px; border-bottom: 1px solid #1e293b; font-size: 14px; }}
        .steps-table tr:hover {{ background: #243048; }}

        /* Screenshots */
        .screenshots {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
            gap: 12px;
            margin: 16px 0;
        }}
        .screenshot-card {{
            background: #0f172a;
            border-radius: 8px;
            overflow: hidden;
            border: 1px solid #334155;
        }}
        .screenshot-card img {{
            width: 100%;
            height: auto;
            display: block;
        }}
        .screenshot-card .caption {{
            padding: 8px;
            font-size: 12px;
            color: #94a3b8;
            text-align: center;
        }}

        /* RICE Table */
        .rice-table {{ width: 100%; border-collapse: collapse; margin: 12px 0; }}
        .rice-table th {{
            background: #334155;
            padding: 10px 14px;
            text-align: center;
            font-size: 13px;
            color: #94a3b8;
        }}
        .rice-table td {{
            padding: 10px 14px;
            text-align: center;
            border-bottom: 1px solid #334155;
        }}
        .rice-table td:first-child {{ text-align: left; font-weight: 600; }}

        /* Logcat */
        .logcat {{
            background: #0f172a;
            border-radius: 8px;
            padding: 12px;
            font-family: 'Cascadia Code', 'Fira Code', monospace;
            font-size: 12px;
            line-height: 1.5;
            max-height: 300px;
            overflow-y: auto;
            white-space: pre-wrap;
            word-break: break-all;
            color: #94a3b8;
            border: 1px solid #334155;
        }}

        /* Badge */
        .badge {{
            display: inline-block;
            padding: 3px 10px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 600;
            color: white;
        }}
        .badge-pass {{ background: #10b981; }}
        .badge-fail {{ background: #ef4444; }}
        .badge-error {{ background: #f59e0b; }}
        .badge-skip {{ background: #6b7280; }}

        /* Print */
        @media print {{
            body {{ background: white; color: black; }}
            .section-body {{ display: block !important; }}
            .card {{ border: 1px solid #ccc; }}
        }}

        .chevron {{ transition: transform 0.3s; }}
        .section.open .chevron {{ transform: rotate(90deg); }}
    </style>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <div class="header">
            <h1>🤖 Miko3 Talents Test Report</h1>
            <div class="meta">
                Generated: {now.strftime('%B %d, %Y at %H:%M:%S')} |
                Duration: {duration:.1f}s |
                Framework v1.0.0
            </div>
        </div>

        <!-- Summary Cards -->
        <div class="summary-grid">
            <div class="card total">
                <div class="label">Total Tests</div>
                <div class="value">{total}</div>
            </div>
            <div class="card pass">
                <div class="label">Passed</div>
                <div class="value">{passed}</div>
            </div>
            <div class="card fail">
                <div class="label">Failed</div>
                <div class="value">{failed}</div>
            </div>
            <div class="card error">
                <div class="label">Errors</div>
                <div class="value">{errors}</div>
            </div>
            <div class="card time">
                <div class="label">Total Duration</div>
                <div class="value">{duration:.1f}s</div>
            </div>
        </div>

        <!-- Progress Bar -->
        <div class="progress-bar">
            <div class="progress-fill" style="width:{(passed/max(total,1))*100:.0f}%;background:linear-gradient(90deg,#10b981,#34d399);"></div>
        </div>

        <!-- Device Info -->
        {self._build_device_section()}

        <!-- Test Results -->
        <h2 style="margin:24px 0 16px;color:#60a5fa;">📋 Test Results</h2>
        {self._build_results_sections()}

        <!-- RICE POT Analysis -->
        <h2 style="margin:24px 0 16px;color:#a78bfa;">📊 RICE POT Prioritization</h2>
        {self._build_rice_section(rice_data)}

        <!-- Footer -->
        <div style="text-align:center;padding:24px;color:#475569;font-size:13px;">
            Miko3 Talents Automation Framework v1.0.0 • Report generated with ❤️
        </div>
    </div>

    <script>
        // Toggle sections
        document.querySelectorAll('.section-header').forEach(header => {{
            header.addEventListener('click', () => {{
                header.parentElement.classList.toggle('open');
            }});
        }});

        // Auto-expand failed tests
        document.querySelectorAll('.section[data-status="FAILED"], .section[data-status="ERROR"]').forEach(s => {{
            s.classList.add('open');
        }});
    </script>
</body>
</html>"""

    def _build_device_section(self) -> str:
        """Build the device info section."""
        if not self.device_info:
            return ""

        rows = ""
        for key, value in self.device_info.items():
            display_key = key.replace("_", " ").title()
            rows += f"<tr><td>{display_key}</td><td>{value}</td></tr>"

        return f"""
        <div class="device-info">
            <h3>📱 Device Information</h3>
            <table>{rows}</table>
        </div>"""

    def _build_results_sections(self) -> str:
        """Build individual test result sections."""
        html = ""
        for result in self.results:
            status = result.status.value
            badge_class = {
                "PASSED": "badge-pass",
                "FAILED": "badge-fail",
                "ERROR": "badge-error",
            }.get(status, "badge-skip")

            # Steps table
            steps_html = ""
            if result.steps:
                steps_rows = ""
                for step in result.steps:
                    step_badge = self._status_badge(step.status)
                    err = f'<br><small style="color:#ef4444;">{step.error_message}</small>' if step.error_message else ""
                    steps_rows += f"""
                    <tr>
                        <td>{step.name}</td>
                        <td>{step_badge}</td>
                        <td>{step.duration:.1f}s</td>
                        <td>{step.description}{err}</td>
                    </tr>"""

                steps_html = f"""
                <h4 style="margin:12px 0 8px;color:#94a3b8;">Steps</h4>
                <table class="steps-table">
                    <thead><tr><th>Step</th><th>Status</th><th>Duration</th><th>Details</th></tr></thead>
                    <tbody>{steps_rows}</tbody>
                </table>"""

            # Screenshots
            screenshots_html = ""
            if result.screenshots and self.embed_screenshots:
                cards = ""
                for ss in result.screenshots[:12]:  # Limit to 12
                    encoded = self._encode_screenshot(ss)
                    if encoded:
                        name = os.path.basename(ss)
                        cards += f"""
                        <div class="screenshot-card">
                            <img src="{encoded}" alt="{name}" loading="lazy">
                            <div class="caption">{name}</div>
                        </div>"""

                if cards:
                    screenshots_html = f"""
                    <h4 style="margin:12px 0 8px;color:#94a3b8;">📸 Screenshots</h4>
                    <div class="screenshots">{cards}</div>"""

            # Logcat excerpt
            logcat_html = ""
            if result.logcat_excerpt:
                excerpt = result.logcat_excerpt[:5000]  # Limit size
                excerpt = excerpt.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                logcat_html = f"""
                <h4 style="margin:12px 0 8px;color:#94a3b8;">📝 Logcat</h4>
                <div class="logcat">{excerpt}</div>"""

            # Error message
            error_html = ""
            if result.error_message:
                error_html = f"""
                <div style="background:#7f1d1d;padding:12px;border-radius:8px;margin:12px 0;border:1px solid #ef4444;">
                    <strong>Error:</strong> {result.error_message}
                </div>"""

            html += f"""
            <div class="section" data-status="{status}">
                <div class="section-header">
                    <h3>
                        <span class="chevron">▶</span>
                        {result.talent_name}
                        <span class="badge {badge_class}" style="margin-left:12px;">{status}</span>
                    </h3>
                    <span style="color:#94a3b8;font-size:13px;">
                        {result.step_summary} • {result.duration:.1f}s
                    </span>
                </div>
                <div class="section-body">
                    {error_html}
                    {steps_html}
                    {screenshots_html}
                    {logcat_html}
                </div>
            </div>"""

        return html

    def _build_rice_section(self, rice_data: dict) -> str:
        """Build the RICE POT analysis section."""
        rows = ""
        for score in rice_data.get("scores", []):
            rows += f"""
            <tr>
                <td>{score['talent_name']}</td>
                <td>{score['reach']}</td>
                <td>{score['impact']}</td>
                <td>{score['confidence']}</td>
                <td>{score['effort']}</td>
                <td style="font-weight:700;color:#60a5fa;">{score['rice_score']}</td>
                <td>{score['priority']}</td>
            </tr>"""

        return f"""
        <div class="section open">
            <div class="section-header">
                <h3><span class="chevron">▶</span> RICE POT Analysis</h3>
            </div>
            <div class="section-body">
                <table class="rice-table">
                    <thead>
                        <tr>
                            <th>Talent</th>
                            <th>Reach</th>
                            <th>Impact</th>
                            <th>Confidence</th>
                            <th>Effort</th>
                            <th>Score</th>
                            <th>Priority</th>
                        </tr>
                    </thead>
                    <tbody>{rows}</tbody>
                </table>
                <p style="margin-top:12px;color:#94a3b8;font-size:13px;">
                    Formula: Score = (Reach × Impact × Confidence) / Effort — Higher is better
                </p>
            </div>
        </div>"""
