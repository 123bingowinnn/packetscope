import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from packetscope.cli import run_cli
from packetscope.measure import (
    MeasurementResult,
    PingResult,
    TargetSpec,
    TracerouteResult,
    _measure_http_ms,
    aggregate_measurement_runs,
    measure_target,
    normalize_target,
    parse_ping_output,
    parse_traceroute_output,
)
from packetscope.report import build_conclusion, build_main_finding, write_reports


MAC_PING_OUTPUT = """PING example.com (93.184.216.34): 56 data bytes
64 bytes from 93.184.216.34: icmp_seq=0 ttl=56 time=9.213 ms
64 bytes from 93.184.216.34: icmp_seq=1 ttl=56 time=10.317 ms

--- example.com ping statistics ---
2 packets transmitted, 2 packets received, 0.0% packet loss
round-trip min/avg/max/stddev = 9.213/9.765/10.317/0.552 ms
"""


LINUX_PING_OUTPUT = """PING example.com (93.184.216.34) 56(84) bytes of data.
64 bytes from 93.184.216.34: icmp_seq=1 ttl=56 time=8.20 ms

--- example.com ping statistics ---
1 packets transmitted, 1 received, 0% packet loss, time 0ms
rtt min/avg/max/mdev = 8.200/8.200/8.200/0.000 ms
"""

PING_100_LOSS_OUTPUT = """PING example.com (93.184.216.34): 56 data bytes

--- example.com ping statistics ---
3 packets transmitted, 0 packets received, 100.0% packet loss
"""


TRACEROUTE_OUTPUT = """traceroute to example.com (93.184.216.34), 20 hops max, 52 byte packets
 1  router.local (192.168.1.1)  1.232 ms  1.108 ms  1.055 ms
 2  10.0.0.1 (10.0.0.1)  5.412 ms  5.300 ms  5.277 ms
 3  * * *
 4  example.com (93.184.216.34)  30.100 ms  30.204 ms  30.188 ms
"""


def sample_result(target="example.com"):
    return MeasurementResult(
        target=target,
        host=target,
        scheme="https",
        dns_ms=12.3,
        tcp_ms=22.4,
        http_ms=45.6,
        ping_min_ms=8.7,
        ping_avg_ms=9.8,
        ping_max_ms=11.2,
        packet_loss_percent=0.0,
        hop_count=4,
        http_status=200,
        traceroute_raw=TRACEROUTE_OUTPUT,
        errors=[],
    )


def score_result(target, score, errors=None):
    return MeasurementResult(
        target=target,
        host=target,
        scheme="https",
        dns_ms=10.0,
        tcp_ms=20.0,
        tls_ms=5.0,
        http_ms=float(score) - 45.0,
        ping_min_ms=9.0,
        ping_avg_ms=10.0,
        ping_max_ms=11.0,
        ping_jitter_ms=1.0,
        packet_loss_percent=0.0,
        hop_count=4,
        http_status=200,
        traceroute_raw=TRACEROUTE_OUTPUT,
        errors=errors or [],
    )


class NormalizeTargetTests(unittest.TestCase):
    def test_plain_domain_defaults_to_https(self):
        target = normalize_target("example.com")

        self.assertEqual(target.original, "example.com")
        self.assertEqual(target.host, "example.com")
        self.assertEqual(target.scheme, "https")
        self.assertEqual(target.port, 443)
        self.assertEqual(target.path, "/")

    def test_url_with_path_preserves_scheme_host_and_path(self):
        target = normalize_target("http://example.com/docs/page?q=1")

        self.assertEqual(target.host, "example.com")
        self.assertEqual(target.scheme, "http")
        self.assertEqual(target.port, 80)
        self.assertEqual(target.path, "/docs/page?q=1")


class ParserTests(unittest.TestCase):
    def test_parse_macos_ping_output(self):
        result = parse_ping_output(MAC_PING_OUTPUT)

        self.assertEqual(result.min_ms, 9.213)
        self.assertEqual(result.avg_ms, 9.765)
        self.assertEqual(result.max_ms, 10.317)
        self.assertEqual(result.jitter_ms, 0.552)
        self.assertEqual(result.packet_loss_percent, 0.0)

    def test_parse_linux_ping_output(self):
        result = parse_ping_output(LINUX_PING_OUTPUT)

        self.assertEqual(result.min_ms, 8.2)
        self.assertEqual(result.avg_ms, 8.2)
        self.assertEqual(result.max_ms, 8.2)
        self.assertEqual(result.jitter_ms, 0.0)
        self.assertEqual(result.packet_loss_percent, 0.0)

    def test_parse_ping_output_with_full_packet_loss_has_no_average_rtt(self):
        result = parse_ping_output(PING_100_LOSS_OUTPUT)

        self.assertIsNone(result.min_ms)
        self.assertIsNone(result.avg_ms)
        self.assertIsNone(result.max_ms)
        self.assertEqual(result.packet_loss_percent, 100.0)

    def test_parse_traceroute_output_counts_hops_and_keeps_raw_text(self):
        result = parse_traceroute_output(TRACEROUTE_OUTPUT)

        self.assertEqual(result.hop_count, 4)
        self.assertIn("router.local", result.raw)
        self.assertIn("* * *", result.raw)

    def test_https_http_timing_starts_after_tls_handshake(self):
        target = TargetSpec(
            original="example.com",
            scheme="https",
            host="example.com",
            port=443,
            path="/",
        )
        raw_socket = mock.Mock()
        tls_socket = mock.Mock()
        tls_socket.recv.return_value = b"HTTP/1.1 200 OK\r\n\r\n"
        events = []

        def wrap_socket(sock, server_hostname):
            events.append("tls handshake finished")
            return tls_socket

        times = iter([100.0, 100.25, 200.0, 200.25])

        def now():
            events.append("timer read")
            return next(times)

        with mock.patch("packetscope.measure.socket.create_connection", return_value=raw_socket), \
            mock.patch("packetscope.measure.ssl.create_default_context") as context_factory, \
            mock.patch("packetscope.measure.time.perf_counter", side_effect=now):
            context_factory.return_value.wrap_socket.side_effect = wrap_socket

            tls_ms, elapsed_ms, status = _measure_http_ms(target, timeout=5.0)

        self.assertEqual(tls_ms, 250.0)
        self.assertEqual(elapsed_ms, 250.0)
        self.assertEqual(status, 200)
        self.assertEqual(events[0], "timer read")
        self.assertEqual(events[1], "tls handshake finished")
        raw_socket.sendall.assert_not_called()
        tls_socket.sendall.assert_called_once()

    def test_measure_target_reports_progress_events(self):
        events = []

        def fake_http(target, timeout, progress_callback):
            progress_callback("tls", "started", operation="ssl.wrap_socket")
            progress_callback("tls", "done", duration_ms=3.0, result="3.0 ms")
            progress_callback("http", "started", operation="GET / HTTP/1.1")
            progress_callback("http", "done", duration_ms=4.0, result="HTTP 200")
            return 3.0, 4.0, 200

        with mock.patch("packetscope.measure._measure_dns_details", return_value=(1.0, ["93.184.216.34"])), \
            mock.patch("packetscope.measure._measure_tcp_ms", return_value=2.0), \
            mock.patch("packetscope.measure._measure_http_ms", side_effect=fake_http), \
            mock.patch(
                "packetscope.measure._run_ping",
                return_value=PingResult(5.0, 6.0, 7.0, 0.2, 0.0, "ping output"),
            ), \
            mock.patch(
                "packetscope.measure._run_traceroute",
                return_value=TracerouteResult(4, TRACEROUTE_OUTPUT),
            ):
            result = measure_target("https://example.com", progress_callback=events.append)

        self.assertEqual(result.http_status, 200)
        observed = [(event["stage"], event["status"]) for event in events]
        self.assertIn(("dns", "started"), observed)
        self.assertIn(("dns", "done"), observed)
        self.assertIn(("tcp", "started"), observed)
        self.assertIn(("tls", "started"), observed)
        self.assertIn(("http", "done"), observed)
        self.assertIn(("ping", "started"), observed)
        self.assertIn(("trace", "done"), observed)

    def test_measurement_result_classifies_error_types(self):
        result = MeasurementResult(
            target="broken.example",
            host="broken.example",
            scheme="https",
            dns_ms=None,
            tcp_ms=None,
            http_ms=None,
            ping_avg_ms=None,
            packet_loss_percent=None,
            hop_count=None,
            http_status=None,
            traceroute_raw="",
            errors=[
                "DNS failed: lookup timed out",
                "run 2: TLS failed: certificate error",
                "Traceroute failed: no hops parsed",
            ],
        )

        self.assertEqual(result.error_types, ["dns", "tls", "traceroute"])
        self.assertEqual(result.success_rate_percent, 0.0)


class ReportTests(unittest.TestCase):
    def test_aggregate_measurement_runs_calculates_average_ranges_and_stability(self):
        first = sample_result()
        second = sample_result()
        second.dns_ms = 18.3
        second.tcp_ms = 30.4
        second.http_ms = 55.6
        second.tls_ms = 12.0
        second.ping_min_ms = 10.7
        second.ping_avg_ms = 13.8
        second.ping_max_ms = 16.2
        second.ping_jitter_ms = 0.8
        second.hop_count = 6
        second.errors = ["Traceroute failed: timed out"]

        result = aggregate_measurement_runs([first, second])

        self.assertEqual(result.run_count, 2)
        self.assertEqual(result.dns_ms, 15.3)
        self.assertEqual(result.dns_min_ms, 12.3)
        self.assertEqual(result.dns_max_ms, 18.3)
        self.assertEqual(result.tcp_ms, 26.4)
        self.assertEqual(result.tcp_min_ms, 22.4)
        self.assertEqual(result.tcp_max_ms, 30.4)
        self.assertEqual(result.http_ms, 50.6)
        self.assertEqual(result.http_min_ms, 45.6)
        self.assertEqual(result.http_max_ms, 55.6)
        self.assertEqual(result.tls_ms, 12.0)
        self.assertEqual(result.ping_avg_ms, 11.8)
        self.assertEqual(result.ping_jitter_ms, 0.8)
        self.assertEqual(result.ping_avg_min_ms, 9.8)
        self.assertEqual(result.ping_avg_max_ms, 13.8)
        self.assertEqual(result.ping_stdev_ms, 2.0)
        self.assertEqual(result.visible_latency_score_ms, 116.1)
        self.assertEqual(result.success_rate_percent, 91.7)
        self.assertEqual(result.hop_count, 5)
        self.assertEqual(result.error_types, ["traceroute"])
        self.assertIn("run 2: Traceroute failed", result.error_text)

    def test_aggregate_measurement_runs_rejects_mixed_targets(self):
        with self.assertRaises(ValueError):
            aggregate_measurement_runs([sample_result("one.example"), sample_result("two.example")])

    def test_write_reports_creates_json_csv_and_html(self):
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            result = sample_result()

            written = write_reports([result], out_dir)

            self.assertEqual(written["json"], out_dir / "results.json")
            self.assertEqual(written["csv"], out_dir / "results.csv")
            self.assertEqual(written["html"], out_dir / "report.html")

            data = json.loads((out_dir / "results.json").read_text(encoding="utf-8"))
            self.assertEqual(data["schema_version"], 2)
            self.assertIn("run", data)
            self.assertIn("environment", data)
            self.assertIn("python_version", data["environment"])
            self.assertIn("packetscope_version", data["environment"])
            self.assertEqual(data["results"][0]["target"], "example.com")
            self.assertEqual(data["results"][0]["http_status"], 200)
            self.assertEqual(data["results"][0]["ping_min_ms"], 8.7)
            self.assertEqual(data["results"][0]["ping_max_ms"], 11.2)
            self.assertIn("tls_ms", data["results"][0])
            self.assertIn("ping_jitter_ms", data["results"][0])
            self.assertIn("success_rate_percent", data["results"][0])
            self.assertIn("error_types", data["results"][0])

            with (out_dir / "results.csv").open(encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(
                rows[0].keys(),
                {
                    "target",
                    "dns_ms",
                    "tcp_ms",
                    "tls_ms",
                    "http_ms",
                    "ping_min_ms",
                    "ping_avg_ms",
                    "ping_max_ms",
                    "ping_jitter_ms",
                    "run_count",
                    "dns_min_ms",
                    "dns_max_ms",
                    "tcp_min_ms",
                    "tcp_max_ms",
                    "http_min_ms",
                    "http_max_ms",
                    "ping_avg_min_ms",
                    "ping_avg_max_ms",
                    "ping_stdev_ms",
                    "visible_latency_score_ms",
                    "success_rate_percent",
                    "packet_loss_percent",
                    "hop_count",
                    "http_status",
                    "error_types",
                    "error",
                },
            )

            html = (out_dir / "report.html").read_text(encoding="utf-8")
            self.assertIn("PacketScope Report", html)
            self.assertIn('rel="icon"', html)
            self.assertIn("min-width: 980px", html)
            self.assertIn("Main Finding", html)
            self.assertIn("Measurement Method", html)
            self.assertIn("Experiment Metadata", html)
            self.assertIn("Experiment Insights", html)
            self.assertIn("example.com", html)
            self.assertIn("Latency Comparison", html)
            self.assertIn("Stability Summary", html)
            self.assertIn("Ping RTT Range", html)
            self.assertIn("Diagnostic Summary", html)
            self.assertIn("Observation Limits", html)
            self.assertIn("Conclusion", html)

    def test_write_reports_accepts_run_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp)

            write_reports(
                [sample_result()],
                out_dir,
                run_metadata={
                    "command": "experiment",
                    "targets": ["example.com"],
                    "runs": 3,
                    "mock": True,
                },
            )

            data = json.loads((out_dir / "results.json").read_text(encoding="utf-8"))

        self.assertEqual(data["schema_version"], 2)
        self.assertEqual(data["run"]["command"], "experiment")
        self.assertEqual(data["run"]["targets"], ["example.com"])
        self.assertEqual(data["run"]["runs"], 3)
        self.assertTrue(data["run"]["mock"])

    def test_conclusion_mentions_fastest_site_and_latency_relationship(self):
        results = [
            sample_result("fast.example"),
            MeasurementResult(
                target="slow.example",
                host="slow.example",
                scheme="https",
                dns_ms=20.0,
                tcp_ms=50.0,
                http_ms=90.0,
                ping_min_ms=35.0,
                ping_avg_ms=40.0,
                ping_max_ms=45.0,
                packet_loss_percent=0.0,
                hop_count=9,
                http_status=200,
                traceroute_raw="",
                errors=[],
            ),
        ]

        conclusion = build_conclusion(results)

        self.assertIn("fast.example", conclusion)
        self.assertIn("RTT", conclusion)
        self.assertIn("hop", conclusion)
        self.assertIn("ICMP", conclusion)
        self.assertIn("response time", conclusion)

    def test_main_finding_summarizes_fastest_slowest_and_hop_context(self):
        results = [
            sample_result("fast.example"),
            MeasurementResult(
                target="slow.example",
                host="slow.example",
                scheme="https",
                dns_ms=20.0,
                tcp_ms=50.0,
                tls_ms=25.0,
                http_ms=90.0,
                ping_min_ms=35.0,
                ping_avg_ms=40.0,
                ping_max_ms=45.0,
                packet_loss_percent=0.0,
                hop_count=None,
                http_status=200,
                traceroute_raw="",
                errors=["Traceroute failed: timed out"],
            ),
        ]

        finding = build_main_finding(results)

        self.assertIn("fast.example", finding)
        self.assertIn("slow.example", finding)
        self.assertIn("HTTP response", finding)
        self.assertIn("routing hops", finding)
        self.assertIn("Traceroute was incomplete", finding)

    def test_html_marks_missing_hop_count_as_not_available(self):
        result = sample_result()
        result.hop_count = None
        result.traceroute_raw = ""
        result.errors = ["Traceroute failed: timed out"]

        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            write_reports([result], out_dir)

            html = (out_dir / "report.html").read_text(encoding="utf-8")

        self.assertIn("N/A", html)
        self.assertIn("missing traceroute", html)


class DiagnosisTests(unittest.TestCase):
    def test_diagnose_results_identifies_bottleneck_stability_and_limits(self):
        from packetscope.diagnose import diagnose_results

        result = sample_result("slow.example")
        result.http_ms = 120.0
        result.tls_ms = 30.0
        result.ping_jitter_ms = 2.0

        diagnosis = diagnose_results([result])
        target = diagnosis["targets"][0]

        self.assertEqual(diagnosis["schema_version"], 2)
        self.assertEqual(target["target"], "slow.example")
        self.assertEqual(target["bottleneck_layer"], "http")
        self.assertEqual(target["bottleneck_value_ms"], 120.0)
        self.assertEqual(target["stability_score"], 96.0)
        self.assertTrue(any("HTTP" in item for item in target["evidence"]))
        self.assertTrue(any("ICMP" in item for item in target["limitations"]))

    def test_diagnose_results_uses_unknown_when_no_metrics_exist(self):
        from packetscope.diagnose import diagnose_results

        result = MeasurementResult(
            target="empty.example",
            host="empty.example",
            scheme="https",
            dns_ms=None,
            tcp_ms=None,
            tls_ms=None,
            http_ms=None,
            ping_avg_ms=None,
            packet_loss_percent=None,
            hop_count=None,
            http_status=None,
            traceroute_raw="",
            errors=[],
        )

        target = diagnose_results([result])["targets"][0]

        self.assertEqual(target["bottleneck_layer"], "unknown")
        self.assertIsNone(target["stability_score"])
        self.assertTrue(any("No successful timing" in item for item in target["evidence"]))

    def test_write_diagnosis_report_creates_json_csv_and_html(self):
        from packetscope.diagnose import write_diagnosis_report

        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            written = write_diagnosis_report([sample_result()], out_dir)

            self.assertEqual(written["json"], out_dir / "diagnosis.json")
            self.assertEqual(written["csv"], out_dir / "diagnosis.csv")
            self.assertEqual(written["html"], out_dir / "diagnosis.html")
            self.assertIn("PacketScope Diagnosis", (out_dir / "diagnosis.html").read_text(encoding="utf-8"))


class CompareTests(unittest.TestCase):
    def test_compare_results_classifies_common_new_and_missing_targets(self):
        from packetscope.compare import compare_results

        baseline = [
            score_result("improved.example", 100.0),
            score_result("regressed.example", 100.0),
            score_result("stable.example", 100.0),
            score_result("missing.example", 100.0),
        ]
        current = [
            score_result("improved.example", 70.0),
            score_result("regressed.example", 130.0, errors=["HTTP failed: timeout"]),
            score_result("stable.example", 108.0),
            score_result("new.example", 100.0),
        ]

        comparison = compare_results(baseline, current)
        common = {item["target"]: item for item in comparison["common_targets"]}

        self.assertEqual(comparison["schema_version"], 2)
        self.assertEqual(comparison["thresholds"]["absolute_ms"], 10.0)
        self.assertEqual(comparison["thresholds"]["percent"], 10.0)
        self.assertEqual(common["improved.example"]["status"], "improved")
        self.assertEqual(common["regressed.example"]["status"], "regressed")
        self.assertEqual(common["stable.example"]["status"], "stable")
        self.assertEqual(common["regressed.example"]["failure_change"], "worse")
        self.assertEqual(comparison["new_targets"], ["new.example"])
        self.assertEqual(comparison["missing_targets"], ["missing.example"])

    def test_write_compare_report_creates_json_csv_and_html(self):
        from packetscope.compare import write_compare_report

        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            written = write_compare_report(
                [score_result("example.com", 100.0)],
                [score_result("example.com", 130.0)],
                out_dir,
            )

            self.assertEqual(written["json"], out_dir / "compare.json")
            self.assertEqual(written["csv"], out_dir / "compare.csv")
            self.assertEqual(written["html"], out_dir / "compare.html")
            self.assertIn("PacketScope Compare", (out_dir / "compare.html").read_text(encoding="utf-8"))


class CliTests(unittest.TestCase):
    def test_experiment_mock_writes_reports(self):
        with tempfile.TemporaryDirectory() as tmp:
            exit_code = run_cli(["experiment", "--mock", "--out", tmp])

            self.assertEqual(exit_code, 0)
            self.assertTrue((Path(tmp) / "results.json").exists())
            self.assertTrue((Path(tmp) / "results.csv").exists())
            self.assertTrue((Path(tmp) / "report.html").exists())

    def test_experiment_passes_traceroute_options_to_measurement(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch("packetscope.cli.measure_target") as measure:
            measure.return_value = sample_result()

            exit_code = run_cli([
                "experiment",
                "example.com",
                "--out",
                tmp,
                "--trace-wait",
                "1.5",
                "--trace-timeout",
                "12",
            ])

        self.assertEqual(exit_code, 0)
        measure.assert_called_once_with(
            "example.com",
            timeout=5.0,
            ping_count=3,
            max_hops=20,
            trace_wait=1.5,
            trace_timeout=12.0,
        )

    def test_experiment_runs_same_target_multiple_times_and_aggregates(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch("packetscope.cli.measure_target") as measure:
            first = sample_result()
            second = sample_result()
            second.dns_ms = 18.3
            second.ping_avg_ms = 13.8
            measure.side_effect = [first, second]

            exit_code = run_cli([
                "experiment",
                "example.com",
                "--out",
                tmp,
                "--runs",
                "2",
            ])

            self.assertEqual(exit_code, 0)
            self.assertEqual(measure.call_count, 2)
            data = json.loads((Path(tmp) / "results.json").read_text(encoding="utf-8"))
            self.assertEqual(data["results"][0]["run_count"], 2)
            self.assertEqual(data["results"][0]["dns_ms"], 15.3)
            self.assertEqual(data["results"][0]["dns_min_ms"], 12.3)
            self.assertEqual(data["results"][0]["dns_max_ms"], 18.3)
            self.assertEqual(data["results"][0]["ping_stdev_ms"], 2.0)

    def test_experiment_mock_runs_preserve_target_differences(self):
        with tempfile.TemporaryDirectory() as tmp:
            exit_code = run_cli([
                "experiment",
                "example.com",
                "python.org",
                "--mock",
                "--runs",
                "2",
                "--out",
                tmp,
            ])

            self.assertEqual(exit_code, 0)
            data = json.loads((Path(tmp) / "results.json").read_text(encoding="utf-8"))
            self.assertEqual(data["results"][0]["target"], "example.com")
            self.assertEqual(data["results"][0]["dns_ms"], 8.0)
            self.assertEqual(data["results"][0]["run_count"], 2)
            self.assertEqual(data["results"][1]["target"], "python.org")
            self.assertEqual(data["results"][1]["dns_ms"], 12.5)
            self.assertEqual(data["results"][1]["run_count"], 2)

    def test_runs_must_be_positive(self):
        with self.assertRaises(SystemExit):
            run_cli(["experiment", "--mock", "--runs", "0"])

    def test_report_command_regenerates_outputs_from_existing_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            source_dir = Path(tmp) / "source"
            out_dir = Path(tmp) / "regenerated"
            write_reports([sample_result()], source_dir)

            exit_code = run_cli(["report", str(source_dir / "results.json"), "--out", str(out_dir)])

            self.assertEqual(exit_code, 0)
            self.assertTrue((out_dir / "results.json").exists())
            self.assertTrue((out_dir / "results.csv").exists())
            self.assertTrue((out_dir / "report.html").exists())

    def test_report_command_accepts_results_json_without_new_ping_range_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            source_dir = Path(tmp) / "source"
            out_dir = Path(tmp) / "regenerated"
            source_dir.mkdir()
            old_result = sample_result().to_dict()
            del old_result["ping_min_ms"]
            del old_result["ping_max_ms"]
            for key in [
                "run_count",
                "dns_min_ms",
                "dns_max_ms",
                "tcp_min_ms",
                "tcp_max_ms",
                "http_min_ms",
                "http_max_ms",
                "ping_avg_min_ms",
                "ping_avg_max_ms",
                "ping_stdev_ms",
                "visible_latency_score_ms",
            ]:
                old_result.pop(key, None)
            (source_dir / "results.json").write_text(
                json.dumps({"results": [old_result]}),
                encoding="utf-8",
            )

            exit_code = run_cli(["report", str(source_dir / "results.json"), "--out", str(out_dir)])

            self.assertEqual(exit_code, 0)
            data = json.loads((out_dir / "results.json").read_text(encoding="utf-8"))
            self.assertIsNone(data["results"][0]["ping_min_ms"])
            self.assertIsNone(data["results"][0]["ping_max_ms"])
            self.assertEqual(data["results"][0]["run_count"], 1)

    def test_report_command_accepts_results_json_without_schema_v2_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            source_dir = Path(tmp) / "source"
            out_dir = Path(tmp) / "regenerated"
            source_dir.mkdir()
            old_result = sample_result().to_dict()
            for key in [
                "tls_ms",
                "ping_jitter_ms",
                "success_rate_percent",
                "error_types",
                "started_at",
                "finished_at",
                "duration_ms",
            ]:
                old_result.pop(key, None)
            (source_dir / "results.json").write_text(
                json.dumps({"results": [old_result]}),
                encoding="utf-8",
            )

            exit_code = run_cli(["report", str(source_dir / "results.json"), "--out", str(out_dir)])

            self.assertEqual(exit_code, 0)
            data = json.loads((out_dir / "results.json").read_text(encoding="utf-8"))
            self.assertEqual(data["schema_version"], 2)
            self.assertIsNone(data["results"][0]["tls_ms"])
            self.assertEqual(data["results"][0]["error_types"], [])

    def test_diagnose_command_writes_report_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            source_dir = Path(tmp) / "source"
            out_dir = Path(tmp) / "diagnosis"
            write_reports([sample_result()], source_dir)

            exit_code = run_cli(["diagnose", str(source_dir / "results.json"), "--out", str(out_dir)])

            self.assertEqual(exit_code, 0)
            self.assertTrue((out_dir / "diagnosis.json").exists())
            self.assertTrue((out_dir / "diagnosis.csv").exists())
            self.assertTrue((out_dir / "diagnosis.html").exists())

    def test_compare_command_writes_report_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            baseline_dir = Path(tmp) / "baseline"
            current_dir = Path(tmp) / "current"
            out_dir = Path(tmp) / "compare"
            write_reports([score_result("example.com", 100.0)], baseline_dir)
            write_reports([score_result("example.com", 130.0)], current_dir)

            exit_code = run_cli([
                "compare",
                str(baseline_dir / "results.json"),
                str(current_dir / "results.json"),
                "--out",
                str(out_dir),
            ])

            self.assertEqual(exit_code, 0)
            self.assertTrue((out_dir / "compare.json").exists())
            self.assertTrue((out_dir / "compare.csv").exists())
            self.assertTrue((out_dir / "compare.html").exists())


class WebServerTests(unittest.TestCase):
    def test_measure_for_web_returns_real_measurement_payload_shape(self):
        from packetscope.server import measure_for_web

        with mock.patch("packetscope.server._validate_targets", return_value=["example.com"]), \
            mock.patch("packetscope.server.measure_target", return_value=sample_result()):
            payload = measure_for_web(["example.com"])

        self.assertTrue(payload["ok"])
        self.assertEqual(payload["measurement_origin"], "PacketScope server network")
        self.assertEqual(payload["targets"], ["example.com"])
        self.assertEqual(payload["results"][0]["target"], "example.com")
        self.assertEqual(payload["diagnosis"]["targets"][0]["target"], "example.com")

    def test_measure_for_web_compares_two_targets(self):
        from packetscope.server import measure_for_web

        with mock.patch("packetscope.server._validate_targets", return_value=["fast.example", "slow.example"]), \
            mock.patch(
                "packetscope.server.measure_target",
                side_effect=[score_result("fast.example", 90.0), score_result("slow.example", 130.0)],
            ):
            payload = measure_for_web(["fast.example", "slow.example"])

        self.assertEqual(payload["comparison"]["winner"], "fast.example")
        self.assertEqual(payload["comparison"]["delta_ms"], 40.0)

    def test_online_target_validation_rejects_private_addresses(self):
        from packetscope.server import PublicTargetError, _validate_targets

        with self.assertRaises(PublicTargetError):
            _validate_targets(["http://127.0.0.1:8000"])

        with self.assertRaises(PublicTargetError):
            _validate_targets(["localhost"])

    def test_web_command_starts_server_with_requested_host_and_port(self):
        with mock.patch("packetscope.server.run_server") as run_server:
            exit_code = run_cli(["web", "--host", "0.0.0.0", "--port", "9999"])

        self.assertEqual(exit_code, 0)
        run_server.assert_called_once_with("0.0.0.0", 9999)


if __name__ == "__main__":
    unittest.main()
