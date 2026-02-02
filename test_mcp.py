"""
Test Blender MCP get_current_state tool directly.
Verifies that the skeleton response is smaller than the full scene data.
"""
import subprocess
import json
import sys

def test_blender_mcp():
    print("=" * 60)
    print("BLENDER MCP TEST - get_current_state")
    print("=" * 60)

    # Path to the installed MCP executable
    mcp_exe = r"C:\Users\nickm\AppData\Roaming\OneController\mcps\blender-mcp\blender-mcp.exe"

    # Initialize request
    init_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "test-client", "version": "1.0.0"}
        }
    }

    # Tool call request for get_current_state
    tool_request = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {
            "name": "get_current_state",
            "arguments": {}
        }
    }

    print(f"\n[1] Starting MCP: {mcp_exe}")

    try:
        # Start MCP process
        proc = subprocess.Popen(
            [mcp_exe],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        # Send initialize
        print("[2] Sending initialize request...")
        proc.stdin.write(json.dumps(init_request) + "\n")
        proc.stdin.flush()

        # Read init response
        init_response = proc.stdout.readline()
        print(f"[3] Init response: {len(init_response)} bytes")

        # Send initialized notification
        initialized_notification = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized",
            "params": {}
        }
        proc.stdin.write(json.dumps(initialized_notification) + "\n")
        proc.stdin.flush()

        # Send tool call
        print("[4] Calling get_current_state...")
        proc.stdin.write(json.dumps(tool_request) + "\n")
        proc.stdin.flush()

        # Read tool response
        tool_response = proc.stdout.readline()
        response_size = len(tool_response)

        print(f"\n[5] RESPONSE SIZE: {response_size:,} bytes ({response_size/1024:.1f} KB)")

        # Parse and analyze
        try:
            response_json = json.loads(tool_response)
            if "result" in response_json:
                content = response_json["result"].get("content", [])
                if content and len(content) > 0:
                    text_content = content[0].get("text", "")
                    text_size = len(text_content)
                    print(f"[6] TEXT CONTENT SIZE: {text_size:,} bytes ({text_size/1024:.1f} KB)")

                    # Parse the skeleton
                    skeleton = json.loads(text_content)
                    print(f"\n[7] SKELETON ANALYSIS:")
                    print(f"    Scene name: {skeleton.get('scene_name')}")
                    print(f"    Object count: {skeleton.get('object_count')}")
                    print(f"    Objects in list: {len(skeleton.get('objects', []))}")
                    print(f"    Selected objects: {skeleton.get('selected_objects')}")
                    print(f"    Active object: {skeleton.get('active_object')}")
                    print(f"    Cameras: {len(skeleton.get('cameras', []))}")
                    print(f"    Lights: {len(skeleton.get('lights', []))}")

                    # Check if objects have only name/type
                    if skeleton.get("objects"):
                        sample = skeleton["objects"][0]
                        print(f"\n[8] SAMPLE OBJECT STRUCTURE:")
                        print(f"    Keys: {list(sample.keys())}")
                        print(f"    Sample: {sample}")

                        # Verify skeleton format
                        if set(sample.keys()) == {"name", "type"}:
                            print("\n[OK] Objects contain ONLY name and type (skeleton format)")
                        else:
                            print(f"\n[WARNING] Objects have extra keys: {set(sample.keys()) - {'name', 'type'}}")

                    # Size comparison
                    print(f"\n[9] SIZE ASSESSMENT:")
                    if text_size < 50000:
                        print(f"    [OK] Response is under 50KB - good for AI context")
                    elif text_size < 100000:
                        print(f"    [WARNING] Response is 50-100KB - borderline")
                    else:
                        print(f"    [FAIL] Response is over 100KB - too large for AI context")

            elif "error" in response_json:
                print(f"[ERROR] {response_json['error']}")
        except json.JSONDecodeError as e:
            print(f"[ERROR] Failed to parse response: {e}")
            print(f"Raw response: {tool_response[:500]}...")

        # Cleanup
        proc.terminate()
        proc.wait(timeout=5)

    except FileNotFoundError:
        print(f"[ERROR] MCP executable not found: {mcp_exe}")
        print("Make sure Blender MCP is installed in OneController.")
    except Exception as e:
        print(f"[ERROR] {type(e).__name__}: {e}")

if __name__ == "__main__":
    test_blender_mcp()
