"""
Performance test for Blender MCP context tools.

Tests latency of context tools to ensure they don't hold up the real-time frontend.
Target: Each context call should complete in < 100ms for smooth UX.

Usage:
    python test_context_performance.py
"""
import subprocess
import json
import time
import sys
import os
import statistics

class MCPClient:
    """Simple MCP JSON-RPC client."""

    def __init__(self, process):
        self.process = process
        self.request_id = 0

    def call_tool(self, tool_name: str, arguments: dict = None, timeout: float = 10.0) -> tuple:
        """Call an MCP tool and return (result, latency_ms)."""
        if arguments is None:
            arguments = {}

        self.request_id += 1
        request = {
            "jsonrpc": "2.0",
            "id": self.request_id,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }

        request_json = json.dumps(request) + "\n"

        # Measure latency
        start = time.perf_counter()

        self.process.stdin.write(request_json.encode())
        self.process.stdin.flush()

        # Read response
        while time.perf_counter() - start < timeout:
            line = self.process.stdout.readline()
            if line:
                try:
                    response = json.loads(line.decode().strip())
                    if response.get("id") == self.request_id:
                        latency_ms = (time.perf_counter() - start) * 1000
                        return response, latency_ms
                except json.JSONDecodeError:
                    continue
            time.sleep(0.001)

        return None, timeout * 1000

    def initialize(self):
        """Send initialize request."""
        request = {
            "jsonrpc": "2.0",
            "id": 0,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "perf-test", "version": "1.0.0"}
            }
        }
        self.process.stdin.write((json.dumps(request) + "\n").encode())
        self.process.stdin.flush()

        for _ in range(50):
            line = self.process.stdout.readline()
            if line:
                try:
                    response = json.loads(line.decode().strip())
                    if response.get("id") == 0:
                        return True
                except:
                    pass
            time.sleep(0.1)
        return False


def run_performance_test():
    """Run performance tests on context tools."""
    print("=" * 70)
    print("BLENDER MCP CONTEXT PERFORMANCE TEST")
    print("Target: < 100ms per context call")
    print("=" * 70)
    print("\nMake sure Blender is running with the addon enabled!")
    print()

    # Start MCP server
    exe_path = os.path.join(os.path.dirname(__file__), "dist", "blender-mcp.exe")
    if os.path.exists(exe_path):
        cmd = [exe_path]
    else:
        cmd = [sys.executable, "main.py"]

    print(f"Starting: {' '.join(cmd)}")

    process = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=os.path.dirname(__file__) or "."
    )

    time.sleep(2)
    client = MCPClient(process)

    if not client.initialize():
        print("ERROR: Failed to initialize MCP connection")
        process.terminate()
        return False

    time.sleep(1)
    print("Connected to MCP server\n")

    # Context tools to test
    context_tools = [
        ("get_full_context", {}),
        ("get_scene_info", {}),
        ("get_viewport_state", {}),
        ("get_modifier_stack", {}),
        ("get_node_tree", {"material_name": None}),
    ]

    results = {}
    iterations = 5  # Run each test multiple times

    for tool_name, args in context_tools:
        print(f"\nTesting: {tool_name}")
        print("-" * 40)

        latencies = []
        errors = 0

        for i in range(iterations):
            result, latency_ms = client.call_tool(tool_name, args)

            if result and "error" not in result:
                latencies.append(latency_ms)
                status = "OK" if latency_ms < 100 else "SLOW"
                print(f"  Run {i+1}: {latency_ms:.1f}ms [{status}]")
            else:
                errors += 1
                error_msg = result.get("error") if result else "Timeout"
                print(f"  Run {i+1}: ERROR - {error_msg}")

        if latencies:
            avg = statistics.mean(latencies)
            min_val = min(latencies)
            max_val = max(latencies)

            results[tool_name] = {
                "avg_ms": avg,
                "min_ms": min_val,
                "max_ms": max_val,
                "errors": errors,
                "pass": avg < 100
            }

            status = "PASS" if avg < 100 else "FAIL"
            print(f"  Avg: {avg:.1f}ms | Min: {min_val:.1f}ms | Max: {max_val:.1f}ms [{status}]")
        else:
            results[tool_name] = {"avg_ms": 0, "errors": iterations, "pass": False}
            print(f"  ALL FAILED ({errors} errors)")

    # Cleanup
    process.terminate()
    try:
        process.wait(timeout=3)
    except:
        process.kill()

    # Summary
    print("\n" + "=" * 70)
    print("PERFORMANCE SUMMARY")
    print("=" * 70)
    print(f"{'Tool':<25} {'Avg (ms)':<12} {'Status':<10}")
    print("-" * 50)

    all_pass = True
    for tool_name, data in results.items():
        if data["errors"] == iterations:
            status = "ERROR"
            all_pass = False
        elif data["pass"]:
            status = "PASS"
        else:
            status = "SLOW"
            all_pass = False
        print(f"{tool_name:<25} {data['avg_ms']:<12.1f} {status:<10}")

    print("-" * 50)

    if all_pass:
        print("\nALL CONTEXT TOOLS PASS (<100ms)")
        print("Ready for real-time frontend use!")
    else:
        print("\nSOME TOOLS NEED OPTIMIZATION")
        print("Review slow tools above")

    print("=" * 70)

    return all_pass


if __name__ == "__main__":
    success = run_performance_test()
    sys.exit(0 if success else 1)
