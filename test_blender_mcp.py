"""
Test Blender MCP tools via MCP JSON-RPC communication.

This script:
1. Starts blender-mcp as a subprocess
2. Tests all the new AI Control System tools
3. Requires Blender to be running with the addon enabled

Usage:
    python test_blender_mcp.py
"""
import subprocess
import threading
import json
import time
import sys
import os

class MCPClient:
    """Simple MCP JSON-RPC client that communicates via stdio."""

    def __init__(self, process):
        self.process = process
        self.request_id = 0
        self._lock = threading.Lock()

    def call_tool(self, tool_name: str, arguments: dict = None, timeout: float = 30.0) -> tuple:
        """Call an MCP tool and return (result, latency_ms)."""
        if arguments is None:
            arguments = {}

        with self._lock:
            self.request_id += 1
            request_id = self.request_id

        request = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }

        request_json = json.dumps(request) + "\n"
        print(f"\n[CLIENT] Calling: {tool_name}")
        if arguments:
            print(f"         Args: {json.dumps(arguments, indent=2)[:200]}")

        start = time.perf_counter()
        self.process.stdin.write(request_json.encode())
        self.process.stdin.flush()

        # Read response
        while time.perf_counter() - start < timeout:
            line = self.process.stdout.readline()
            if line:
                try:
                    response = json.loads(line.decode().strip())
                    if response.get("id") == request_id:
                        latency_ms = (time.perf_counter() - start) * 1000
                        return response, latency_ms
                except json.JSONDecodeError:
                    continue
            time.sleep(0.01)

        raise TimeoutError(f"No response for {tool_name} within {timeout}s")

    def initialize(self):
        """Send initialize request to MCP server."""
        request = {
            "jsonrpc": "2.0",
            "id": 0,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "blender-mcp-test", "version": "1.0.0"}
            }
        }
        request_json = json.dumps(request) + "\n"
        self.process.stdin.write(request_json.encode())
        self.process.stdin.flush()

        # Read response
        for _ in range(50):  # More retries for startup
            line = self.process.stdout.readline()
            if line:
                try:
                    response = json.loads(line.decode().strip())
                    if response.get("id") == 0:
                        server_info = response.get('result', {}).get('serverInfo', {})
                        print(f"[CLIENT] Connected to: {server_info}")
                        return response
                except json.JSONDecodeError:
                    continue
            time.sleep(0.1)

        raise RuntimeError("Failed to initialize MCP connection")


def print_result(result: dict, max_len: int = 1000, latency_ms: float = None):
    """Pretty print a tool result."""
    latency_str = f" [{latency_ms:.0f}ms]" if latency_ms else ""

    if "error" in result:
        print(f"  [ERROR]{latency_str} {result['error']}")
        return False

    content = result.get("result", {}).get("content", [])
    if content:
        text = content[0].get("text", "")
        try:
            # Try to parse as JSON for pretty printing
            data = json.loads(text)
            formatted = json.dumps(data, indent=2)
            if len(formatted) > max_len:
                print(f"  [OK]{latency_str} Response ({len(formatted)} chars):")
                print(f"  {formatted[:max_len]}...")
            else:
                print(f"  [OK]{latency_str} Response:")
                print(f"  {formatted}")
        except:
            if len(text) > max_len:
                print(f"  [OK]{latency_str} Response ({len(text)} chars): {text[:max_len]}...")
            else:
                print(f"  [OK]{latency_str} Response: {text}")
        return True
    else:
        print(f"  [WARN]{latency_str} Empty response")
        return False


def test_blender_mcp():
    """Test Blender MCP tools."""
    print("=" * 70)
    print("BLENDER MCP TEST - AI Control System v1.6.1")
    print("Make sure Blender is running with the addon enabled!")
    print("=" * 70)

    # Start blender-mcp
    print("\n1. Starting blender-mcp subprocess...")

    # Use exe for final testing, Python for development
    exe_path = os.path.join(os.path.dirname(__file__), "dist", "blender-mcp.exe")
    if os.path.exists(exe_path):
        cmd = [exe_path]
        env = os.environ.copy()
        print(f"   Using: {exe_path}")
    else:
        # Fallback to Python for development
        env = os.environ.copy()
        src_path = os.path.join(os.path.dirname(__file__), "src")
        env["PYTHONPATH"] = src_path + os.pathsep + env.get("PYTHONPATH", "")
        cmd = [sys.executable, "main.py"]
        print(f"   Using: python main.py (PYTHONPATH includes src)")

    mcp_process = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=os.path.dirname(__file__) or ".",
        env=env
    )

    # Wait for startup
    time.sleep(3)

    # Background thread to print stderr
    def print_stderr():
        while True:
            line = mcp_process.stderr.readline()
            if line:
                msg = line.decode().strip()
                if msg and "INFO" not in msg:  # Skip INFO logs
                    print(f"   [STDERR] {msg}")
            else:
                break

    stderr_thread = threading.Thread(target=print_stderr, daemon=True)
    stderr_thread.start()

    client = MCPClient(mcp_process)
    passed = 0
    failed = 0

    try:
        # Initialize
        print("\n2. Initializing MCP connection...")
        client.initialize()
        time.sleep(1)

        # Test: get_full_context
        print("\n" + "=" * 50)
        print("TEST: get_full_context [CONTEXT]")
        print("=" * 50)
        try:
            result, latency = client.call_tool("get_full_context", {})
            if print_result(result, latency_ms=latency):
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"  [FAIL] {e}")
            failed += 1

        # Test: get_scene_info
        print("\n" + "=" * 50)
        print("TEST: get_scene_info [CONTEXT]")
        print("=" * 50)
        try:
            result, latency = client.call_tool("get_scene_info", {})
            if print_result(result, latency_ms=latency):
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"  [FAIL] {e}")
            failed += 1

        # Test: get_viewport_state
        print("\n" + "=" * 50)
        print("TEST: get_viewport_state [CONTEXT]")
        print("=" * 50)
        try:
            result, latency = client.call_tool("get_viewport_state", {})
            if print_result(result, latency_ms=latency):
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"  [FAIL] {e}")
            failed += 1

        # Test: get_modifier_stack (for active object)
        print("\n" + "=" * 50)
        print("TEST: get_modifier_stack [CONTEXT]")
        print("=" * 50)
        try:
            result, latency = client.call_tool("get_modifier_stack", {})
            if print_result(result, latency_ms=latency):
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"  [FAIL] {e}")
            failed += 1

        # Test: add_primitive (create a cube)
        print("\n" + "=" * 50)
        print("TEST: add_primitive (CUBE) [COMMAND]")
        print("=" * 50)
        try:
            result, latency = client.call_tool("add_primitive", {
                "primitive_type": "CUBE",
                "location": [2, 0, 0],
                "name": "TestCube"
            })
            if print_result(result, latency_ms=latency):
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"  [FAIL] {e}")
            failed += 1

        # Test: select_object
        print("\n" + "=" * 50)
        print("TEST: select_object (TestCube) [COMMAND]")
        print("=" * 50)
        try:
            result, latency = client.call_tool("select_object", {
                "object_name": "TestCube"
            })
            if print_result(result, latency_ms=latency):
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"  [FAIL] {e}")
            failed += 1

        # Test: add_modifier
        print("\n" + "=" * 50)
        print("TEST: add_modifier (SUBSURF) [COMMAND]")
        print("=" * 50)
        try:
            result, latency = client.call_tool("add_modifier", {
                "modifier_type": "SUBSURF",
                "settings": {"levels": 2}
            })
            if print_result(result, latency_ms=latency):
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"  [FAIL] {e}")
            failed += 1

        # Test: create_material
        print("\n" + "=" * 50)
        print("TEST: create_material [COMMAND]")
        print("=" * 50)
        try:
            result, latency = client.call_tool("create_material", {
                "name": "TestMaterial",
                "assign_to_active": True
            })
            if print_result(result, latency_ms=latency):
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"  [FAIL] {e}")
            failed += 1

        # Test: get_node_tree
        print("\n" + "=" * 50)
        print("TEST: get_node_tree (TestMaterial) [CONTEXT]")
        print("=" * 50)
        try:
            result, latency = client.call_tool("get_node_tree", {
                "material_name": "TestMaterial"
            })
            if print_result(result, latency_ms=latency):
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"  [FAIL] {e}")
            failed += 1

        # Test: set_viewport_shading
        print("\n" + "=" * 50)
        print("TEST: set_viewport_shading (MATERIAL) [COMMAND]")
        print("=" * 50)
        try:
            result, latency = client.call_tool("set_viewport_shading", {
                "shading_type": "MATERIAL"
            })
            if print_result(result, latency_ms=latency):
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"  [FAIL] {e}")
            failed += 1

        # Test: transform_object
        print("\n" + "=" * 50)
        print("TEST: transform_object [COMMAND]")
        print("=" * 50)
        try:
            result, latency = client.call_tool("transform_object", {
                "object_name": "TestCube",
                "location": [3, 1, 0.5],
                "rotation": [0, 0, 45],
                "scale": [1.5, 1.5, 1.5]
            })
            if print_result(result, latency_ms=latency):
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"  [FAIL] {e}")
            failed += 1

        # Test: execute_action_sequence
        print("\n" + "=" * 50)
        print("TEST: execute_action_sequence (multi-step) [COMMAND]")
        print("=" * 50)
        try:
            result, latency = client.call_tool("execute_action_sequence", {
                "actions": [
                    {"action": "add_primitive", "primitive_type": "SPHERE", "location": [-2, 0, 0], "name": "TestSphere"},
                    {"action": "add_modifier", "modifier_type": "BEVEL", "settings": {"segments": 3}}
                ]
            })
            if print_result(result, max_len=2000, latency_ms=latency):
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"  [FAIL] {e}")
            failed += 1

        # Test: delete_object (cleanup)
        print("\n" + "=" * 50)
        print("TEST: delete_object (cleanup TestCube) [COMMAND]")
        print("=" * 50)
        try:
            result, latency = client.call_tool("delete_object", {
                "object_name": "TestCube"
            })
            if print_result(result, latency_ms=latency):
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"  [FAIL] {e}")
            failed += 1

    finally:
        # Cleanup
        print("\n" + "=" * 70)
        print("Cleaning up...")
        try:
            mcp_process.terminate()
            mcp_process.wait(timeout=5)
        except:
            mcp_process.kill()

    # Summary
    print("\n" + "=" * 70)
    print(f"TEST RESULTS: {passed} passed, {failed} failed")
    if failed == 0:
        print("ALL TESTS PASSED!")
    else:
        print("Some tests failed - check output above")
    print("=" * 70)

    return failed == 0


if __name__ == "__main__":
    success = test_blender_mcp()
    sys.exit(0 if success else 1)
