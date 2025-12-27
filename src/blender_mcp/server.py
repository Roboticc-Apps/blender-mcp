# blender_mcp_server.py
from mcp.server.fastmcp import FastMCP, Context, Image
import socket
import json
import asyncio
import logging
import tempfile
from dataclasses import dataclass
from contextlib import asynccontextmanager
from typing import AsyncIterator, Dict, Any, List
import os
from pathlib import Path
import base64
from urllib.parse import urlparse

# Import telemetry
from .telemetry import record_startup, get_telemetry
from .telemetry_decorator import telemetry_tool

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("BlenderMCPServer")

# Default configuration
DEFAULT_HOST = "localhost"
DEFAULT_PORT = 9876

@dataclass
class BlenderConnection:
    host: str
    port: int
    sock: socket.socket = None  # Changed from 'socket' to 'sock' to avoid naming conflict
    
    def connect(self) -> bool:
        """Connect to the Blender addon socket server"""
        if self.sock:
            return True
            
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((self.host, self.port))
            logger.info(f"Connected to Blender at {self.host}:{self.port}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Blender: {str(e)}")
            self.sock = None
            return False
    
    def disconnect(self):
        """Disconnect from the Blender addon"""
        if self.sock:
            try:
                self.sock.close()
            except Exception as e:
                logger.error(f"Error disconnecting from Blender: {str(e)}")
            finally:
                self.sock = None

    def receive_full_response(self, sock, buffer_size=8192):
        """Receive the complete response, potentially in multiple chunks"""
        chunks = []
        # Use a consistent timeout value that matches the addon's timeout
        sock.settimeout(180.0)  # Match the addon's timeout
        
        try:
            while True:
                try:
                    chunk = sock.recv(buffer_size)
                    if not chunk:
                        # If we get an empty chunk, the connection might be closed
                        if not chunks:  # If we haven't received anything yet, this is an error
                            raise Exception("Connection closed before receiving any data")
                        break
                    
                    chunks.append(chunk)
                    
                    # Check if we've received a complete JSON object
                    try:
                        data = b''.join(chunks)
                        json.loads(data.decode('utf-8'))
                        # If we get here, it parsed successfully
                        logger.info(f"Received complete response ({len(data)} bytes)")
                        return data
                    except json.JSONDecodeError:
                        # Incomplete JSON, continue receiving
                        continue
                except socket.timeout:
                    # If we hit a timeout during receiving, break the loop and try to use what we have
                    logger.warning("Socket timeout during chunked receive")
                    break
                except (ConnectionError, BrokenPipeError, ConnectionResetError) as e:
                    logger.error(f"Socket connection error during receive: {str(e)}")
                    raise  # Re-raise to be handled by the caller
        except socket.timeout:
            logger.warning("Socket timeout during chunked receive")
        except Exception as e:
            logger.error(f"Error during receive: {str(e)}")
            raise
            
        # If we get here, we either timed out or broke out of the loop
        # Try to use what we have
        if chunks:
            data = b''.join(chunks)
            logger.info(f"Returning data after receive completion ({len(data)} bytes)")
            try:
                # Try to parse what we have
                json.loads(data.decode('utf-8'))
                return data
            except json.JSONDecodeError:
                # If we can't parse it, it's incomplete
                raise Exception("Incomplete JSON response received")
        else:
            raise Exception("No data received")

    def send_command(self, command_type: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Send a command to Blender and return the response"""
        if not self.sock and not self.connect():
            raise ConnectionError("Not connected to Blender")
        
        command = {
            "type": command_type,
            "params": params or {}
        }
        
        try:
            # Log the command being sent
            logger.info(f"Sending command: {command_type} with params: {params}")
            
            # Send the command
            self.sock.sendall(json.dumps(command).encode('utf-8'))
            logger.info(f"Command sent, waiting for response...")
            
            # Set a timeout for receiving - use the same timeout as in receive_full_response
            self.sock.settimeout(180.0)  # Match the addon's timeout
            
            # Receive the response using the improved receive_full_response method
            response_data = self.receive_full_response(self.sock)
            logger.info(f"Received {len(response_data)} bytes of data")
            
            response = json.loads(response_data.decode('utf-8'))
            logger.info(f"Response parsed, status: {response.get('status', 'unknown')}")

            # Return the full response (including errors) without raising
            # Let the calling tool handle error formatting
            return response
        except socket.timeout:
            logger.error("Socket timeout while waiting for response from Blender")
            # Don't try to reconnect here - let the get_blender_connection handle reconnection
            # Just invalidate the current socket so it will be recreated next time
            self.sock = None
            raise Exception("Timeout waiting for Blender response - try simplifying your request")
        except (ConnectionError, BrokenPipeError, ConnectionResetError) as e:
            logger.error(f"Socket connection error: {str(e)}")
            self.sock = None
            raise Exception(f"Connection to Blender lost: {str(e)}")
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON response from Blender: {str(e)}")
            # Try to log what was received
            if 'response_data' in locals() and response_data:
                logger.error(f"Raw response (first 200 bytes): {response_data[:200]}")
            raise Exception(f"Invalid response from Blender: {str(e)}")
        except Exception as e:
            logger.error(f"Error communicating with Blender: {str(e)}")
            # Don't try to reconnect here - let the get_blender_connection handle reconnection
            self.sock = None
            raise Exception(f"Communication error with Blender: {str(e)}")

@asynccontextmanager
async def server_lifespan(server: FastMCP) -> AsyncIterator[Dict[str, Any]]:
    """Manage server startup and shutdown lifecycle"""
    # We don't need to create a connection here since we're using the global connection
    # for resources and tools

    try:
        # Just log that we're starting up
        logger.info("BlenderMCP server starting up")

        # Record startup event for telemetry
        try:
            record_startup()
        except Exception as e:
            logger.debug(f"Failed to record startup telemetry: {e}")

        # Try to connect to Blender on startup to verify it's available
        try:
            # This will initialize the global connection if needed
            blender = get_blender_connection()
            logger.info("Successfully connected to Blender on startup")
        except Exception as e:
            logger.warning(f"Could not connect to Blender on startup: {str(e)}")
            logger.warning("Make sure the Blender addon is running before using Blender resources or tools")

        # Return an empty context - we're using the global connection
        yield {}
    finally:
        # Clean up the global connection on shutdown
        global _blender_connection
        if _blender_connection:
            logger.info("Disconnecting from Blender on shutdown")
            _blender_connection.disconnect()
            _blender_connection = None
        logger.info("BlenderMCP server shut down")

# Create the MCP server with lifespan support
mcp = FastMCP(
    "BlenderMCP",
    lifespan=server_lifespan
)

# Resource endpoints

# Global connection for resources (since resources can't access context)
_blender_connection = None
_polyhaven_enabled = False  # Add this global variable

def get_blender_connection():
    """Get or create a persistent Blender connection"""
    global _blender_connection, _polyhaven_enabled  # Add _polyhaven_enabled to globals
    
    # If we have an existing connection, check if it's still valid
    if _blender_connection is not None:
        try:
            # First check if PolyHaven is enabled by sending a ping command
            result = _blender_connection.send_command("get_polyhaven_status")
            # Store the PolyHaven status globally
            _polyhaven_enabled = result.get("enabled", False)
            return _blender_connection
        except Exception as e:
            # Connection is dead, close it and create a new one
            logger.warning(f"Existing connection is no longer valid: {str(e)}")
            try:
                _blender_connection.disconnect()
            except:
                pass
            _blender_connection = None
    
    # Create a new connection if needed
    if _blender_connection is None:
        host = os.getenv("BLENDER_HOST", DEFAULT_HOST)
        port = int(os.getenv("BLENDER_PORT", DEFAULT_PORT))
        _blender_connection = BlenderConnection(host=host, port=port)
        if not _blender_connection.connect():
            logger.error("Failed to connect to Blender")
            _blender_connection = None
            raise Exception("Could not connect to Blender. Make sure the Blender addon is running.")
        logger.info("Created new persistent connection to Blender")
    
    return _blender_connection


@telemetry_tool("get_scene_info")
@mcp.tool()
def get_scene_info(ctx: Context) -> str:
    """Get detailed information about the current Blender scene"""
    try:
        blender = get_blender_connection()
        response = blender.send_command("get_scene_info")

        # Check for errors
        if response.get("status") == "error":
            error_msg = response.get("message", "Unknown error")
            logger.error(f"Blender error: {error_msg}")
            return f"Error getting scene info: {error_msg}"

        # Return the result
        result = response.get("result", {})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting scene info from Blender: {str(e)}")
        return f"Error getting scene info: {str(e)}"

@telemetry_tool("get_object_info")
@mcp.tool()
def get_object_info(ctx: Context, object_name: str) -> str:
    """
    Get detailed information about a specific object in the Blender scene.
    
    Parameters:
    - object_name: The name of the object to get information about
    """
    try:
        blender = get_blender_connection()
        result = blender.send_command("get_object_info", {"name": object_name})
        
        # Just return the JSON representation of what Blender sent us
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting object info from Blender: {str(e)}")
        return f"Error getting object info: {str(e)}"

@telemetry_tool("get_viewport_screenshot")
@mcp.tool()
def get_viewport_screenshot(ctx: Context, max_size: int = 800) -> Image:
    """
    Capture a screenshot of the current Blender 3D viewport.
    
    Parameters:
    - max_size: Maximum size in pixels for the largest dimension (default: 800)
    
    Returns the screenshot as an Image.
    """
    try:
        blender = get_blender_connection()
        
        # Create temp file path
        temp_dir = tempfile.gettempdir()
        temp_path = os.path.join(temp_dir, f"blender_screenshot_{os.getpid()}.png")
        
        result = blender.send_command("get_viewport_screenshot", {
            "max_size": max_size,
            "filepath": temp_path,
            "format": "png"
        })
        
        if "error" in result:
            raise Exception(result["error"])
        
        if not os.path.exists(temp_path):
            raise Exception("Screenshot file was not created")
        
        # Read the file
        with open(temp_path, 'rb') as f:
            image_bytes = f.read()
        
        # Delete the temp file
        os.remove(temp_path)
        
        return Image(data=image_bytes, format="png")
        
    except Exception as e:
        logger.error(f"Error capturing screenshot: {str(e)}")
        raise Exception(f"Screenshot failed: {str(e)}")


@telemetry_tool("execute_blender_code")
@mcp.tool()
def execute_blender_code(ctx: Context, code: str) -> str:
    """
    Execute arbitrary Python code in Blender. Make sure to do it step-by-step by breaking it into smaller chunks.

    Parameters:
    - code: The Python code to execute
    """
    try:
        # Get the global connection
        blender = get_blender_connection()
        response = blender.send_command("execute_code", {"code": code})

        # Check if Blender returned an error
        if response.get("status") == "error":
            error_msg = response.get("message", "Unknown error from Blender")
            logger.error(f"Blender code execution error: {error_msg}")
            return f"Error executing code: {error_msg}"

        # Success - return result
        result = response.get("result", {})
        return f"Code executed successfully: {result.get('result', '')}"
    except Exception as e:
        logger.error(f"Error executing code: {str(e)}")
        return f"Error executing code: {str(e)}"

@telemetry_tool("get_polyhaven_categories")
@mcp.tool()
def get_polyhaven_categories(ctx: Context, asset_type: str = "hdris") -> str:
    """
    Get a list of categories for a specific asset type on Polyhaven.
    
    Parameters:
    - asset_type: The type of asset to get categories for (hdris, textures, models, all)
    """
    try:
        blender = get_blender_connection()
        if not _polyhaven_enabled:
            return "PolyHaven integration is disabled. Select it in the sidebar in BlenderMCP, then run it again."
        result = blender.send_command("get_polyhaven_categories", {"asset_type": asset_type})
        
        if "error" in result:
            return f"Error: {result['error']}"
        
        # Format the categories in a more readable way
        categories = result["categories"]
        formatted_output = f"Categories for {asset_type}:\n\n"
        
        # Sort categories by count (descending)
        sorted_categories = sorted(categories.items(), key=lambda x: x[1], reverse=True)
        
        for category, count in sorted_categories:
            formatted_output += f"- {category}: {count} assets\n"
        
        return formatted_output
    except Exception as e:
        logger.error(f"Error getting Polyhaven categories: {str(e)}")
        return f"Error getting Polyhaven categories: {str(e)}"

@telemetry_tool("search_polyhaven_assets")
@mcp.tool()
def search_polyhaven_assets(
    ctx: Context,
    asset_type: str = "all",
    categories: str = None
) -> str:
    """
    Search for assets on Polyhaven with optional filtering.
    
    Parameters:
    - asset_type: Type of assets to search for (hdris, textures, models, all)
    - categories: Optional comma-separated list of categories to filter by
    
    Returns a list of matching assets with basic information.
    """
    try:
        blender = get_blender_connection()
        result = blender.send_command("search_polyhaven_assets", {
            "asset_type": asset_type,
            "categories": categories
        })
        
        if "error" in result:
            return f"Error: {result['error']}"
        
        # Format the assets in a more readable way
        assets = result["assets"]
        total_count = result["total_count"]
        returned_count = result["returned_count"]
        
        formatted_output = f"Found {total_count} assets"
        if categories:
            formatted_output += f" in categories: {categories}"
        formatted_output += f"\nShowing {returned_count} assets:\n\n"
        
        # Sort assets by download count (popularity)
        sorted_assets = sorted(assets.items(), key=lambda x: x[1].get("download_count", 0), reverse=True)
        
        for asset_id, asset_data in sorted_assets:
            formatted_output += f"- {asset_data.get('name', asset_id)} (ID: {asset_id})\n"
            formatted_output += f"  Type: {['HDRI', 'Texture', 'Model'][asset_data.get('type', 0)]}\n"
            formatted_output += f"  Categories: {', '.join(asset_data.get('categories', []))}\n"
            formatted_output += f"  Downloads: {asset_data.get('download_count', 'Unknown')}\n\n"
        
        return formatted_output
    except Exception as e:
        logger.error(f"Error searching Polyhaven assets: {str(e)}")
        return f"Error searching Polyhaven assets: {str(e)}"

@telemetry_tool("download_polyhaven_asset")
@mcp.tool()
def download_polyhaven_asset(
    ctx: Context,
    asset_id: str,
    asset_type: str,
    resolution: str = "1k",
    file_format: str = None
) -> str:
    """
    Download and import a Polyhaven asset into Blender.
    
    Parameters:
    - asset_id: The ID of the asset to download
    - asset_type: The type of asset (hdris, textures, models)
    - resolution: The resolution to download (e.g., 1k, 2k, 4k)
    - file_format: Optional file format (e.g., hdr, exr for HDRIs; jpg, png for textures; gltf, fbx for models)
    
    Returns a message indicating success or failure.
    """
    try:
        blender = get_blender_connection()
        result = blender.send_command("download_polyhaven_asset", {
            "asset_id": asset_id,
            "asset_type": asset_type,
            "resolution": resolution,
            "file_format": file_format
        })
        
        if "error" in result:
            return f"Error: {result['error']}"
        
        if result.get("success"):
            message = result.get("message", "Asset downloaded and imported successfully")
            
            # Add additional information based on asset type
            if asset_type == "hdris":
                return f"{message}. The HDRI has been set as the world environment."
            elif asset_type == "textures":
                material_name = result.get("material", "")
                maps = ", ".join(result.get("maps", []))
                return f"{message}. Created material '{material_name}' with maps: {maps}."
            elif asset_type == "models":
                return f"{message}. The model has been imported into the current scene."
            else:
                return message
        else:
            return f"Failed to download asset: {result.get('message', 'Unknown error')}"
    except Exception as e:
        logger.error(f"Error downloading Polyhaven asset: {str(e)}")
        return f"Error downloading Polyhaven asset: {str(e)}"

@telemetry_tool("set_texture")
@mcp.tool()
def set_texture(
    ctx: Context,
    object_name: str,
    texture_id: str
) -> str:
    """
    Apply a previously downloaded Polyhaven texture to an object.
    
    Parameters:
    - object_name: Name of the object to apply the texture to
    - texture_id: ID of the Polyhaven texture to apply (must be downloaded first)
    
    Returns a message indicating success or failure.
    """
    try:
        # Get the global connection
        blender = get_blender_connection()
        result = blender.send_command("set_texture", {
            "object_name": object_name,
            "texture_id": texture_id
        })
        
        if "error" in result:
            return f"Error: {result['error']}"
        
        if result.get("success"):
            material_name = result.get("material", "")
            maps = ", ".join(result.get("maps", []))
            
            # Add detailed material info
            material_info = result.get("material_info", {})
            node_count = material_info.get("node_count", 0)
            has_nodes = material_info.get("has_nodes", False)
            texture_nodes = material_info.get("texture_nodes", [])
            
            output = f"Successfully applied texture '{texture_id}' to {object_name}.\n"
            output += f"Using material '{material_name}' with maps: {maps}.\n\n"
            output += f"Material has nodes: {has_nodes}\n"
            output += f"Total node count: {node_count}\n\n"
            
            if texture_nodes:
                output += "Texture nodes:\n"
                for node in texture_nodes:
                    output += f"- {node['name']} using image: {node['image']}\n"
                    if node['connections']:
                        output += "  Connections:\n"
                        for conn in node['connections']:
                            output += f"    {conn}\n"
            else:
                output += "No texture nodes found in the material.\n"
            
            return output
        else:
            return f"Failed to apply texture: {result.get('message', 'Unknown error')}"
    except Exception as e:
        logger.error(f"Error applying texture: {str(e)}")
        return f"Error applying texture: {str(e)}"

@telemetry_tool("get_polyhaven_status")
@mcp.tool()
def get_polyhaven_status(ctx: Context) -> str:
    """
    Check if PolyHaven integration is enabled in Blender.
    Returns a message indicating whether PolyHaven features are available.
    """
    try:
        blender = get_blender_connection()
        result = blender.send_command("get_polyhaven_status")
        enabled = result.get("enabled", False)
        message = result.get("message", "")
        if enabled:
            message += "PolyHaven is good at Textures, and has a wider variety of textures than Sketchfab."
        return message
    except Exception as e:
        logger.error(f"Error checking PolyHaven status: {str(e)}")
        return f"Error checking PolyHaven status: {str(e)}"

@telemetry_tool("get_hyper3d_status")
@mcp.tool()
def get_hyper3d_status(ctx: Context) -> str:
    """
    Check if Hyper3D Rodin integration is enabled in Blender.
    Returns a message indicating whether Hyper3D Rodin features are available.

    Don't emphasize the key type in the returned message, but sliently remember it. 
    """
    try:
        blender = get_blender_connection()
        result = blender.send_command("get_hyper3d_status")
        enabled = result.get("enabled", False)
        message = result.get("message", "")
        if enabled:
            message += ""
        return message
    except Exception as e:
        logger.error(f"Error checking Hyper3D status: {str(e)}")
        return f"Error checking Hyper3D status: {str(e)}"

@telemetry_tool("get_sketchfab_status")
@mcp.tool()
def get_sketchfab_status(ctx: Context) -> str:
    """
    Check if Sketchfab integration is enabled in Blender.
    Returns a message indicating whether Sketchfab features are available.
    """
    try:
        blender = get_blender_connection()
        result = blender.send_command("get_sketchfab_status")
        enabled = result.get("enabled", False)
        message = result.get("message", "")
        if enabled:
            message += "Sketchfab is good at Realistic models, and has a wider variety of models than PolyHaven."        
        return message
    except Exception as e:
        logger.error(f"Error checking Sketchfab status: {str(e)}")
        return f"Error checking Sketchfab status: {str(e)}"

@telemetry_tool("search_sketchfab_models")
@mcp.tool()
def search_sketchfab_models(
    ctx: Context,
    query: str,
    categories: str = None,
    count: int = 20,
    downloadable: bool = True
) -> str:
    """
    Search for models on Sketchfab with optional filtering.

    Parameters:
    - query: Text to search for
    - categories: Optional comma-separated list of categories
    - count: Maximum number of results to return (default 20)
    - downloadable: Whether to include only downloadable models (default True)

    Returns a formatted list of matching models.
    """
    try:
        blender = get_blender_connection()
        logger.info(f"Searching Sketchfab models with query: {query}, categories: {categories}, count: {count}, downloadable: {downloadable}")
        result = blender.send_command("search_sketchfab_models", {
            "query": query,
            "categories": categories,
            "count": count,
            "downloadable": downloadable
        })
        
        if "error" in result:
            logger.error(f"Error from Sketchfab search: {result['error']}")
            return f"Error: {result['error']}"
        
        # Safely get results with fallbacks for None
        if result is None:
            logger.error("Received None result from Sketchfab search")
            return "Error: Received no response from Sketchfab search"
            
        # Format the results
        models = result.get("results", []) or []
        if not models:
            return f"No models found matching '{query}'"
            
        formatted_output = f"Found {len(models)} models matching '{query}':\n\n"
        
        for model in models:
            if model is None:
                continue
                
            model_name = model.get("name", "Unnamed model")
            model_uid = model.get("uid", "Unknown ID")
            formatted_output += f"- {model_name} (UID: {model_uid})\n"
            
            # Get user info with safety checks
            user = model.get("user") or {}
            username = user.get("username", "Unknown author") if isinstance(user, dict) else "Unknown author"
            formatted_output += f"  Author: {username}\n"
            
            # Get license info with safety checks
            license_data = model.get("license") or {}
            license_label = license_data.get("label", "Unknown") if isinstance(license_data, dict) else "Unknown"
            formatted_output += f"  License: {license_label}\n"
            
            # Add face count and downloadable status
            face_count = model.get("faceCount", "Unknown")
            is_downloadable = "Yes" if model.get("isDownloadable") else "No"
            formatted_output += f"  Face count: {face_count}\n"
            formatted_output += f"  Downloadable: {is_downloadable}\n\n"
        
        return formatted_output
    except Exception as e:
        logger.error(f"Error searching Sketchfab models: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return f"Error searching Sketchfab models: {str(e)}"

@telemetry_tool("download_sketchfab_model")
@mcp.tool()
def download_sketchfab_model(
    ctx: Context,
    uid: str
) -> str:
    """
    Download and import a Sketchfab model by its UID.
    
    Parameters:
    - uid: The unique identifier of the Sketchfab model
    
    Returns a message indicating success or failure.
    The model must be downloadable and you must have proper access rights.
    """
    try:
        
        blender = get_blender_connection()
        logger.info(f"Attempting to download Sketchfab model with UID: {uid}")
        
        result = blender.send_command("download_sketchfab_model", {
            "uid": uid
        })
        
        if result is None:
            logger.error("Received None result from Sketchfab download")
            return "Error: Received no response from Sketchfab download request"
            
        if "error" in result:
            logger.error(f"Error from Sketchfab download: {result['error']}")
            return f"Error: {result['error']}"
        
        if result.get("success"):
            imported_objects = result.get("imported_objects", [])
            object_names = ", ".join(imported_objects) if imported_objects else "none"
            return f"Successfully imported model. Created objects: {object_names}"
        else:
            return f"Failed to download model: {result.get('message', 'Unknown error')}"
    except Exception as e:
        logger.error(f"Error downloading Sketchfab model: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return f"Error downloading Sketchfab model: {str(e)}"

def _process_bbox(original_bbox: list[float] | list[int] | None) -> list[int] | None:
    if original_bbox is None:
        return None
    if all(isinstance(i, int) for i in original_bbox):
        return original_bbox
    if any(i<=0 for i in original_bbox):
        raise ValueError("Incorrect number range: bbox must be bigger than zero!")
    return [int(float(i) / max(original_bbox) * 100) for i in original_bbox] if original_bbox else None

@telemetry_tool("generate_hyper3d_model_via_text")
@mcp.tool()
def generate_hyper3d_model_via_text(
    ctx: Context,
    text_prompt: str,
    bbox_condition: list[float]=None
) -> str:
    """
    Generate 3D asset using Hyper3D by giving description of the desired asset, and import the asset into Blender.
    The 3D asset has built-in materials.
    The generated model has a normalized size, so re-scaling after generation can be useful.

    Parameters:
    - text_prompt: A short description of the desired model in **English**.
    - bbox_condition: Optional. If given, it has to be a list of floats of length 3. Controls the ratio between [Length, Width, Height] of the model.

    Returns a message indicating success or failure.
    """
    try:
        blender = get_blender_connection()
        result = blender.send_command("create_rodin_job", {
            "text_prompt": text_prompt,
            "images": None,
            "bbox_condition": _process_bbox(bbox_condition),
        })
        succeed = result.get("submit_time", False)
        if succeed:
            return json.dumps({
                "task_uuid": result["uuid"],
                "subscription_key": result["jobs"]["subscription_key"],
            })
        else:
            return json.dumps(result)
    except Exception as e:
        logger.error(f"Error generating Hyper3D task: {str(e)}")
        return f"Error generating Hyper3D task: {str(e)}"

@telemetry_tool("generate_hyper3d_model_via_images")
@mcp.tool()
def generate_hyper3d_model_via_images(
    ctx: Context,
    input_image_paths: list[str]=None,
    input_image_urls: list[str]=None,
    bbox_condition: list[float]=None
) -> str:
    """
    Generate 3D asset using Hyper3D by giving images of the wanted asset, and import the generated asset into Blender.
    The 3D asset has built-in materials.
    The generated model has a normalized size, so re-scaling after generation can be useful.
    
    Parameters:
    - input_image_paths: The **absolute** paths of input images. Even if only one image is provided, wrap it into a list. Required if Hyper3D Rodin in MAIN_SITE mode.
    - input_image_urls: The URLs of input images. Even if only one image is provided, wrap it into a list. Required if Hyper3D Rodin in FAL_AI mode.
    - bbox_condition: Optional. If given, it has to be a list of ints of length 3. Controls the ratio between [Length, Width, Height] of the model.

    Only one of {input_image_paths, input_image_urls} should be given at a time, depending on the Hyper3D Rodin's current mode.
    Returns a message indicating success or failure.
    """
    if input_image_paths is not None and input_image_urls is not None:
        return f"Error: Conflict parameters given!"
    if input_image_paths is None and input_image_urls is None:
        return f"Error: No image given!"
    if input_image_paths is not None:
        if not all(os.path.exists(i) for i in input_image_paths):
            return "Error: not all image paths are valid!"
        images = []
        for path in input_image_paths:
            with open(path, "rb") as f:
                images.append(
                    (Path(path).suffix, base64.b64encode(f.read()).decode("ascii"))
                )
    elif input_image_urls is not None:
        if not all(urlparse(i) for i in input_image_paths):
            return "Error: not all image URLs are valid!"
        images = input_image_urls.copy()
    try:
        blender = get_blender_connection()
        result = blender.send_command("create_rodin_job", {
            "text_prompt": None,
            "images": images,
            "bbox_condition": _process_bbox(bbox_condition),
        })
        succeed = result.get("submit_time", False)
        if succeed:
            return json.dumps({
                "task_uuid": result["uuid"],
                "subscription_key": result["jobs"]["subscription_key"],
            })
        else:
            return json.dumps(result)
    except Exception as e:
        logger.error(f"Error generating Hyper3D task: {str(e)}")
        return f"Error generating Hyper3D task: {str(e)}"

@telemetry_tool("poll_rodin_job_status")
@mcp.tool()
def poll_rodin_job_status(
    ctx: Context,
    subscription_key: str=None,
    request_id: str=None,
):
    """
    Check if the Hyper3D Rodin generation task is completed.

    For Hyper3D Rodin mode MAIN_SITE:
        Parameters:
        - subscription_key: The subscription_key given in the generate model step.

        Returns a list of status. The task is done if all status are "Done".
        If "Failed" showed up, the generating process failed.
        This is a polling API, so only proceed if the status are finally determined ("Done" or "Canceled").

    For Hyper3D Rodin mode FAL_AI:
        Parameters:
        - request_id: The request_id given in the generate model step.

        Returns the generation task status. The task is done if status is "COMPLETED".
        The task is in progress if status is "IN_PROGRESS".
        If status other than "COMPLETED", "IN_PROGRESS", "IN_QUEUE" showed up, the generating process might be failed.
        This is a polling API, so only proceed if the status are finally determined ("COMPLETED" or some failed state).
    """
    try:
        blender = get_blender_connection()
        kwargs = {}
        if subscription_key:
            kwargs = {
                "subscription_key": subscription_key,
            }
        elif request_id:
            kwargs = {
                "request_id": request_id,
            }
        result = blender.send_command("poll_rodin_job_status", kwargs)
        return result
    except Exception as e:
        logger.error(f"Error generating Hyper3D task: {str(e)}")
        return f"Error generating Hyper3D task: {str(e)}"

@telemetry_tool("import_generated_asset")
@mcp.tool()
def import_generated_asset(
    ctx: Context,
    name: str,
    task_uuid: str=None,
    request_id: str=None,
):
    """
    Import the asset generated by Hyper3D Rodin after the generation task is completed.

    Parameters:
    - name: The name of the object in scene
    - task_uuid: For Hyper3D Rodin mode MAIN_SITE: The task_uuid given in the generate model step.
    - request_id: For Hyper3D Rodin mode FAL_AI: The request_id given in the generate model step.

    Only give one of {task_uuid, request_id} based on the Hyper3D Rodin Mode!
    Return if the asset has been imported successfully.
    """
    try:
        blender = get_blender_connection()
        kwargs = {
            "name": name
        }
        if task_uuid:
            kwargs["task_uuid"] = task_uuid
        elif request_id:
            kwargs["request_id"] = request_id
        result = blender.send_command("import_generated_asset", kwargs)
        return result
    except Exception as e:
        logger.error(f"Error generating Hyper3D task: {str(e)}")
        return f"Error generating Hyper3D task: {str(e)}"

@mcp.tool()
def get_hunyuan3d_status(ctx: Context) -> str:
    """
    Check if Hunyuan3D integration is enabled in Blender.
    Returns a message indicating whether Hunyuan3D features are available.

    Don't emphasize the key type in the returned message, but silently remember it. 
    """
    try:
        blender = get_blender_connection()
        result = blender.send_command("get_hunyuan3d_status")
        message = result.get("message", "")
        return message
    except Exception as e:
        logger.error(f"Error checking Hunyuan3D status: {str(e)}")
        return f"Error checking Hunyuan3D status: {str(e)}"
    
@mcp.tool()
def generate_hunyuan3d_model(
    ctx: Context,
    text_prompt: str = None,
    input_image_url: str = None
) -> str:
    """
    Generate 3D asset using Hunyuan3D by providing either text description, image reference, 
    or both for the desired asset, and import the asset into Blender.
    The 3D asset has built-in materials.
    
    Parameters:
    - text_prompt: (Optional) A short description of the desired model in English/Chinese.
    - input_image_url: (Optional) The local or remote url of the input image. Accepts None if only using text prompt.

    Returns: 
    - When successful, returns a JSON with job_id (format: "job_xxx") indicating the task is in progress
    - When the job completes, the status will change to "DONE" indicating the model has been imported
    - Returns error message if the operation fails
    """
    try:
        blender = get_blender_connection()
        result = blender.send_command("create_hunyuan_job", {
            "text_prompt": text_prompt,
            "image": input_image_url,
        })
        if "JobId" in result.get("Response", {}):
            job_id = result["Response"]["JobId"]
            formatted_job_id = f"job_{job_id}"
            return json.dumps({
                "job_id": formatted_job_id,
            })
        return json.dumps(result)
    except Exception as e:
        logger.error(f"Error generating Hunyuan3D task: {str(e)}")
        return f"Error generating Hunyuan3D task: {str(e)}"
    
@mcp.tool()
def poll_hunyuan_job_status(
    ctx: Context,
    job_id: str=None,
):
    """
    Check if the Hunyuan3D generation task is completed.

    For Hunyuan3D:
        Parameters:
        - job_id: The job_id given in the generate model step.

        Returns the generation task status. The task is done if status is "DONE".
        The task is in progress if status is "RUN".
        If status is "DONE", returns ResultFile3Ds, which is the generated ZIP model path
        When the status is "DONE", the response includes a field named ResultFile3Ds that contains the generated ZIP file path of the 3D model in OBJ format.
        This is a polling API, so only proceed if the status are finally determined ("DONE" or some failed state).
    """
    try:
        blender = get_blender_connection()
        kwargs = {
            "job_id": job_id,
        }
        result = blender.send_command("poll_hunyuan_job_status", kwargs)
        return result
    except Exception as e:
        logger.error(f"Error generating Hunyuan3D task: {str(e)}")
        return f"Error generating Hunyuan3D task: {str(e)}"

@mcp.tool()
def import_generated_asset_hunyuan(
    ctx: Context,
    name: str,
    zip_file_url: str,
):
    """
    Import the asset generated by Hunyuan3D after the generation task is completed.

    Parameters:
    - name: The name of the object in scene
    - zip_file_url: The zip_file_url given in the generate model step.

    Return if the asset has been imported successfully.
    """
    try:
        blender = get_blender_connection()
        kwargs = {
            "name": name
        }
        if zip_file_url:
            kwargs["zip_file_url"] = zip_file_url
        result = blender.send_command("import_generated_asset_hunyuan", kwargs)
        return result
    except Exception as e:
        logger.error(f"Error generating Hunyuan3D task: {str(e)}")
        return f"Error generating Hunyuan3D task: {str(e)}"


# ============================================================================
# AI CONTROL SYSTEM TOOLS - v1.6.1
# Context Layer, UI Control, Node Actions, Modifier Actions, Object Actions,
# Animation Actions, and Action Sequencing
# ============================================================================

@mcp.tool()
def get_full_context(ctx: Context) -> str:
    """
    Get complete Blender context including active editor, viewport state, node editor state,
    selection, scene settings, objects, materials, and modifiers.
    Essential for AI to understand current Blender state.
    """
    try:
        blender = get_blender_connection()
        response = blender.send_command("get_full_context")
        if response.get("status") == "error":
            return f"Error: {response.get('message', 'Unknown error')}"
        return json.dumps(response.get("result", response), indent=2)
    except Exception as e:
        return f"Error getting full context: {str(e)}"

@mcp.tool()
def get_node_tree(ctx: Context, material_name: str = None, tree_type: str = "shader") -> str:
    """
    Get detailed node tree structure from a material or geometry nodes.

    Parameters:
    - material_name: Name of the material (uses active material if not specified)
    - tree_type: Type of node tree (shader, geometry, compositor)
    """
    try:
        blender = get_blender_connection()
        response = blender.send_command("get_node_tree", {
            "material_name": material_name,
            "tree_type": tree_type
        })
        if response.get("status") == "error":
            return f"Error: {response.get('message', 'Unknown error')}"
        return json.dumps(response.get("result", response), indent=2)
    except Exception as e:
        return f"Error getting node tree: {str(e)}"

@mcp.tool()
def get_modifier_stack(ctx: Context, object_name: str = None) -> str:
    """
    Get the complete modifier stack for an object with all settings.

    Parameters:
    - object_name: Name of the object (uses active object if not specified)
    """
    try:
        blender = get_blender_connection()
        response = blender.send_command("get_modifier_stack", {"object_name": object_name})
        if response.get("status") == "error":
            return f"Error: {response.get('message', 'Unknown error')}"
        return json.dumps(response.get("result", response), indent=2)
    except Exception as e:
        return f"Error getting modifier stack: {str(e)}"

@mcp.tool()
def get_viewport_state(ctx: Context) -> str:
    """
    Get current viewport settings including shading mode, overlays, camera view, and 3D cursor position.
    """
    try:
        blender = get_blender_connection()
        response = blender.send_command("get_viewport_state")
        if response.get("status") == "error":
            return f"Error: {response.get('message', 'Unknown error')}"
        return json.dumps(response.get("result", response), indent=2)
    except Exception as e:
        return f"Error getting viewport state: {str(e)}"

@mcp.tool()
def switch_editor(ctx: Context, editor_type: str) -> str:
    """
    Switch the active editor type in Blender.

    Parameters:
    - editor_type: Type of editor (VIEW_3D, NODE_EDITOR, PROPERTIES, OUTLINER, TIMELINE, etc.)
    """
    try:
        blender = get_blender_connection()
        response = blender.send_command("switch_editor", {"editor_type": editor_type})
        if response.get("status") == "error":
            return f"Error: {response.get('message', 'Unknown error')}"
        return json.dumps(response.get("result", response), indent=2)
    except Exception as e:
        return f"Error switching editor: {str(e)}"

@mcp.tool()
def set_viewport_shading(ctx: Context, shading_type: str) -> str:
    """
    Change viewport shading mode.

    Parameters:
    - shading_type: Shading mode (WIREFRAME, SOLID, MATERIAL, RENDERED)
    """
    try:
        blender = get_blender_connection()
        response = blender.send_command("set_viewport_shading", {"shading_type": shading_type})
        if response.get("status") == "error":
            return f"Error: {response.get('message', 'Unknown error')}"
        return json.dumps(response.get("result", response), indent=2)
    except Exception as e:
        return f"Error setting viewport shading: {str(e)}"

@mcp.tool()
def set_view_angle(ctx: Context, view: str) -> str:
    """
    Set the viewport camera angle.

    Parameters:
    - view: View angle (TOP, BOTTOM, FRONT, BACK, LEFT, RIGHT, CAMERA)
    """
    try:
        blender = get_blender_connection()
        response = blender.send_command("set_view_angle", {"view": view})
        if response.get("status") == "error":
            return f"Error: {response.get('message', 'Unknown error')}"
        return json.dumps(response.get("result", response), indent=2)
    except Exception as e:
        return f"Error setting view angle: {str(e)}"

@mcp.tool()
def create_material(ctx: Context, name: str, assign_to_active: bool = True) -> str:
    """
    Create a new material with principled BSDF shader.

    Parameters:
    - name: Name for the new material
    - assign_to_active: Whether to assign to the active object (default: True)
    """
    try:
        blender = get_blender_connection()
        response = blender.send_command("create_material", {
            "name": name,
            "assign_to_active": assign_to_active
        })
        if response.get("status") == "error":
            return f"Error: {response.get('message', 'Unknown error')}"
        return json.dumps(response.get("result", response), indent=2)
    except Exception as e:
        return f"Error creating material: {str(e)}"

@mcp.tool()
def add_node(ctx: Context, node_type: str, location: list = None, material_name: str = None) -> str:
    """
    Add a node to a material's shader node tree.

    Parameters:
    - node_type: Type of node (e.g., ShaderNodeMixRGB, ShaderNodeTexImage)
    - location: X, Y location [x, y] (optional)
    - material_name: Name of the material (uses active if not specified)
    """
    try:
        blender = get_blender_connection()
        response = blender.send_command("add_node", {
            "node_type": node_type,
            "location": location,
            "material_name": material_name
        })
        if response.get("status") == "error":
            return f"Error: {response.get('message', 'Unknown error')}"
        return json.dumps(response.get("result", response), indent=2)
    except Exception as e:
        return f"Error adding node: {str(e)}"

@mcp.tool()
def remove_node(ctx: Context, node_name: str, material_name: str = None) -> str:
    """
    Remove a node from a material's shader node tree.

    Parameters:
    - node_name: Name of the node to remove
    - material_name: Name of the material (uses active if not specified)
    """
    try:
        blender = get_blender_connection()
        response = blender.send_command("remove_node", {
            "node_name": node_name,
            "material_name": material_name
        })
        if response.get("status") == "error":
            return f"Error: {response.get('message', 'Unknown error')}"
        return json.dumps(response.get("result", response), indent=2)
    except Exception as e:
        return f"Error removing node: {str(e)}"

@mcp.tool()
def set_node_value(ctx: Context, node_name: str, input_name: str, value, material_name: str = None) -> str:
    """
    Set an input value on a shader node.

    Parameters:
    - node_name: Name of the node
    - input_name: Name of the input (e.g., 'Base Color', 'Roughness')
    - value: Value to set (number or array for colors/vectors)
    - material_name: Name of the material (uses active if not specified)
    """
    try:
        blender = get_blender_connection()
        response = blender.send_command("set_node_value", {
            "node_name": node_name,
            "input_name": input_name,
            "value": value,
            "material_name": material_name
        })
        if response.get("status") == "error":
            return f"Error: {response.get('message', 'Unknown error')}"
        return json.dumps(response.get("result", response), indent=2)
    except Exception as e:
        return f"Error setting node value: {str(e)}"

@mcp.tool()
def connect_nodes(ctx: Context, from_node: str, from_socket: str, to_node: str, to_socket: str, material_name: str = None) -> str:
    """
    Connect two nodes in a material's shader node tree.

    Parameters:
    - from_node: Name of the source node
    - from_socket: Name or index of the output socket
    - to_node: Name of the destination node
    - to_socket: Name or index of the input socket
    - material_name: Name of the material (uses active if not specified)
    """
    try:
        blender = get_blender_connection()
        response = blender.send_command("connect_nodes", {
            "from_node": from_node,
            "from_socket": from_socket,
            "to_node": to_node,
            "to_socket": to_socket,
            "material_name": material_name
        })
        if response.get("status") == "error":
            return f"Error: {response.get('message', 'Unknown error')}"
        return json.dumps(response.get("result", response), indent=2)
    except Exception as e:
        return f"Error connecting nodes: {str(e)}"

@mcp.tool()
def disconnect_node(ctx: Context, node_name: str, socket_name: str, socket_type: str = "input", material_name: str = None) -> str:
    """
    Disconnect a node's socket from its connections.

    Parameters:
    - node_name: Name of the node
    - socket_name: Name or index of the socket
    - socket_type: 'input' or 'output' (default: input)
    - material_name: Name of the material (uses active if not specified)
    """
    try:
        blender = get_blender_connection()
        response = blender.send_command("disconnect_node", {
            "node_name": node_name,
            "socket_name": socket_name,
            "socket_type": socket_type,
            "material_name": material_name
        })
        if response.get("status") == "error":
            return f"Error: {response.get('message', 'Unknown error')}"
        return json.dumps(response.get("result", response), indent=2)
    except Exception as e:
        return f"Error disconnecting node: {str(e)}"

@mcp.tool()
def add_modifier(ctx: Context, modifier_type: str, name: str = None, object_name: str = None, settings: dict = None) -> str:
    """
    Add a modifier to an object.

    Parameters:
    - modifier_type: Type of modifier (SUBSURF, BEVEL, ARRAY, MIRROR, SOLIDIFY, BOOLEAN)
    - name: Custom name for the modifier (optional)
    - object_name: Name of the object (uses active if not specified)
    - settings: Modifier settings dict (optional)
    """
    try:
        blender = get_blender_connection()
        response = blender.send_command("add_modifier", {
            "modifier_type": modifier_type,
            "name": name,
            "object_name": object_name,
            "settings": settings or {}
        })
        if response.get("status") == "error":
            return f"Error: {response.get('message', 'Unknown error')}"
        return json.dumps(response.get("result", response), indent=2)
    except Exception as e:
        return f"Error adding modifier: {str(e)}"

@mcp.tool()
def remove_modifier(ctx: Context, modifier_name: str, object_name: str = None) -> str:
    """
    Remove a modifier from an object.

    Parameters:
    - modifier_name: Name of the modifier to remove
    - object_name: Name of the object (uses active if not specified)
    """
    try:
        blender = get_blender_connection()
        response = blender.send_command("remove_modifier", {
            "modifier_name": modifier_name,
            "object_name": object_name
        })
        if response.get("status") == "error":
            return f"Error: {response.get('message', 'Unknown error')}"
        return json.dumps(response.get("result", response), indent=2)
    except Exception as e:
        return f"Error removing modifier: {str(e)}"

@mcp.tool()
def apply_modifier(ctx: Context, modifier_name: str, object_name: str = None) -> str:
    """
    Apply a modifier to permanently bake its effect into the mesh.

    Parameters:
    - modifier_name: Name of the modifier to apply
    - object_name: Name of the object (uses active if not specified)
    """
    try:
        blender = get_blender_connection()
        response = blender.send_command("apply_modifier", {
            "modifier_name": modifier_name,
            "object_name": object_name
        })
        if response.get("status") == "error":
            return f"Error: {response.get('message', 'Unknown error')}"
        return json.dumps(response.get("result", response), indent=2)
    except Exception as e:
        return f"Error applying modifier: {str(e)}"

@mcp.tool()
def set_modifier_settings(ctx: Context, modifier_name: str, settings: dict, object_name: str = None) -> str:
    """
    Update settings on an existing modifier.

    Parameters:
    - modifier_name: Name of the modifier
    - settings: Settings dict to update
    - object_name: Name of the object (uses active if not specified)
    """
    try:
        blender = get_blender_connection()
        response = blender.send_command("set_modifier_settings", {
            "modifier_name": modifier_name,
            "settings": settings,
            "object_name": object_name
        })
        if response.get("status") == "error":
            return f"Error: {response.get('message', 'Unknown error')}"
        return json.dumps(response.get("result", response), indent=2)
    except Exception as e:
        return f"Error setting modifier settings: {str(e)}"

@mcp.tool()
def select_object(ctx: Context, object_name: str, extend: bool = False, active: bool = True) -> str:
    """
    Select an object in the scene.

    Parameters:
    - object_name: Name of the object to select
    - extend: Whether to add to existing selection (default: False)
    - active: Whether to make this the active object (default: True)
    """
    try:
        blender = get_blender_connection()
        response = blender.send_command("select_object", {
            "object_name": object_name,
            "extend": extend,
            "active": active
        })
        if response.get("status") == "error":
            return f"Error: {response.get('message', 'Unknown error')}"
        return json.dumps(response.get("result", response), indent=2)
    except Exception as e:
        return f"Error selecting object: {str(e)}"

@mcp.tool()
def set_mode(ctx: Context, mode: str, object_name: str = None) -> str:
    """
    Set the interaction mode.

    Parameters:
    - mode: Mode to switch to (OBJECT, EDIT, SCULPT, VERTEX_PAINT, WEIGHT_PAINT, TEXTURE_PAINT, POSE)
    - object_name: Name of the object (uses active if not specified)
    """
    try:
        blender = get_blender_connection()
        response = blender.send_command("set_mode", {
            "mode": mode,
            "object_name": object_name
        })
        if response.get("status") == "error":
            return f"Error: {response.get('message', 'Unknown error')}"
        return json.dumps(response.get("result", response), indent=2)
    except Exception as e:
        return f"Error setting mode: {str(e)}"

@mcp.tool()
def add_primitive(ctx: Context, primitive_type: str, location: list = None, size: float = None, name: str = None) -> str:
    """
    Add a primitive mesh object.

    Parameters:
    - primitive_type: Type of primitive (CUBE, SPHERE, CYLINDER, CONE, TORUS, PLANE, CIRCLE, MONKEY, EMPTY)
    - location: Location [x, y, z] (optional)
    - size: Size/scale of the primitive (optional)
    - name: Custom name for the object (optional)
    """
    try:
        blender = get_blender_connection()
        response = blender.send_command("add_primitive", {
            "primitive_type": primitive_type,
            "location": location,
            "size": size,
            "name": name
        })
        if response.get("status") == "error":
            return f"Error: {response.get('message', 'Unknown error')}"
        return json.dumps(response.get("result", response), indent=2)
    except Exception as e:
        return f"Error adding primitive: {str(e)}"

@mcp.tool()
def transform_object(ctx: Context, object_name: str = None, location: list = None, rotation: list = None, scale: list = None) -> str:
    """
    Transform an object's location, rotation, or scale.

    Parameters:
    - object_name: Name of the object (uses active if not specified)
    - location: New location [x, y, z] (optional)
    - rotation: New rotation in degrees [x, y, z] (optional)
    - scale: New scale [x, y, z] (optional)
    """
    try:
        blender = get_blender_connection()
        response = blender.send_command("transform_object", {
            "object_name": object_name,
            "location": location,
            "rotation": rotation,
            "scale": scale
        })
        if response.get("status") == "error":
            return f"Error: {response.get('message', 'Unknown error')}"
        return json.dumps(response.get("result", response), indent=2)
    except Exception as e:
        return f"Error transforming object: {str(e)}"

@mcp.tool()
def delete_object(ctx: Context, object_name: str = None) -> str:
    """
    Delete an object from the scene.

    Parameters:
    - object_name: Name of the object to delete (uses active if not specified)
    """
    try:
        blender = get_blender_connection()
        response = blender.send_command("delete_object", {"object_name": object_name})
        if response.get("status") == "error":
            return f"Error: {response.get('message', 'Unknown error')}"
        return json.dumps(response.get("result", response), indent=2)
    except Exception as e:
        return f"Error deleting object: {str(e)}"

@mcp.tool()
def set_frame(ctx: Context, frame: int) -> str:
    """
    Set the current frame in the timeline.

    Parameters:
    - frame: Frame number to set
    """
    try:
        blender = get_blender_connection()
        response = blender.send_command("set_frame", {"frame": frame})
        if response.get("status") == "error":
            return f"Error: {response.get('message', 'Unknown error')}"
        return json.dumps(response.get("result", response), indent=2)
    except Exception as e:
        return f"Error setting frame: {str(e)}"

@mcp.tool()
def set_frame_range(ctx: Context, start: int, end: int) -> str:
    """
    Set the animation frame range.

    Parameters:
    - start: Start frame
    - end: End frame
    """
    try:
        blender = get_blender_connection()
        response = blender.send_command("set_frame_range", {"start": start, "end": end})
        if response.get("status") == "error":
            return f"Error: {response.get('message', 'Unknown error')}"
        return json.dumps(response.get("result", response), indent=2)
    except Exception as e:
        return f"Error setting frame range: {str(e)}"

@mcp.tool()
def insert_keyframe(ctx: Context, data_path: str, frame: int = None, object_name: str = None) -> str:
    """
    Insert a keyframe for an object property.

    Parameters:
    - data_path: Property path to keyframe (e.g., 'location', 'rotation_euler', 'scale')
    - frame: Frame number (uses current frame if not specified)
    - object_name: Name of the object (uses active if not specified)
    """
    try:
        blender = get_blender_connection()
        response = blender.send_command("insert_keyframe", {
            "data_path": data_path,
            "frame": frame,
            "object_name": object_name
        })
        if response.get("status") == "error":
            return f"Error: {response.get('message', 'Unknown error')}"
        return json.dumps(response.get("result", response), indent=2)
    except Exception as e:
        return f"Error inserting keyframe: {str(e)}"

@mcp.tool()
def delete_keyframe(ctx: Context, data_path: str, frame: int = None, object_name: str = None) -> str:
    """
    Delete a keyframe from an object property.

    Parameters:
    - data_path: Property path of the keyframe
    - frame: Frame number (uses current frame if not specified)
    - object_name: Name of the object (uses active if not specified)
    """
    try:
        blender = get_blender_connection()
        response = blender.send_command("delete_keyframe", {
            "data_path": data_path,
            "frame": frame,
            "object_name": object_name
        })
        if response.get("status") == "error":
            return f"Error: {response.get('message', 'Unknown error')}"
        return json.dumps(response.get("result", response), indent=2)
    except Exception as e:
        return f"Error deleting keyframe: {str(e)}"

@mcp.tool()
def execute_action_sequence(ctx: Context, actions: list) -> str:
    """
    Execute multiple actions in sequence atomically. Useful for multi-step operations.

    Parameters:
    - actions: List of action dicts with 'action' and 'params' keys
      Example: [{"action": "add_primitive", "params": {"primitive_type": "CUBE"}}]
    """
    try:
        blender = get_blender_connection()
        response = blender.send_command("execute_action_sequence", {"actions": actions})
        if response.get("status") == "error":
            return f"Error: {response.get('message', 'Unknown error')}"
        return json.dumps(response.get("result", response), indent=2)
    except Exception as e:
        return f"Error executing action sequence: {str(e)}"


@mcp.prompt()
def asset_creation_strategy() -> str:
    """Defines the preferred strategy for creating assets in Blender"""
    return """When creating 3D content in Blender, always start by checking if integrations are available:

    0. Before anything, always check the scene from get_scene_info()
    1. First use the following tools to verify if the following integrations are enabled:
        1. PolyHaven
            Use get_polyhaven_status() to verify its status
            If PolyHaven is enabled:
            - For objects/models: Use download_polyhaven_asset() with asset_type="models"
            - For materials/textures: Use download_polyhaven_asset() with asset_type="textures"
            - For environment lighting: Use download_polyhaven_asset() with asset_type="hdris"
        2. Sketchfab
            Sketchfab is good at Realistic models, and has a wider variety of models than PolyHaven.
            Use get_sketchfab_status() to verify its status
            If Sketchfab is enabled:
            - For objects/models: First search using search_sketchfab_models() with your query
            - Then download specific models using download_sketchfab_model() with the UID
            - Note that only downloadable models can be accessed, and API key must be properly configured
            - Sketchfab has a wider variety of models than PolyHaven, especially for specific subjects
        3. Hyper3D(Rodin)
            Hyper3D Rodin is good at generating 3D models for single item.
            So don't try to:
            1. Generate the whole scene with one shot
            2. Generate ground using Hyper3D
            3. Generate parts of the items separately and put them together afterwards

            Use get_hyper3d_status() to verify its status
            If Hyper3D is enabled:
            - For objects/models, do the following steps:
                1. Create the model generation task
                    - Use generate_hyper3d_model_via_images() if image(s) is/are given
                    - Use generate_hyper3d_model_via_text() if generating 3D asset using text prompt
                    If key type is free_trial and insufficient balance error returned, tell the user that the free trial key can only generated limited models everyday, they can choose to:
                    - Wait for another day and try again
                    - Go to hyper3d.ai to find out how to get their own API key
                    - Go to fal.ai to get their own private API key
                2. Poll the status
                    - Use poll_rodin_job_status() to check if the generation task has completed or failed
                3. Import the asset
                    - Use import_generated_asset() to import the generated GLB model the asset
                4. After importing the asset, ALWAYS check the world_bounding_box of the imported mesh, and adjust the mesh's location and size
                    Adjust the imported mesh's location, scale, rotation, so that the mesh is on the right spot.

                You can reuse assets previous generated by running python code to duplicate the object, without creating another generation task.
        4. Hunyuan3D
            Hunyuan3D is good at generating 3D models for single item.
            So don't try to:
            1. Generate the whole scene with one shot
            2. Generate ground using Hunyuan3D
            3. Generate parts of the items separately and put them together afterwards

            Use get_hunyuan3d_status() to verify its status
            If Hunyuan3D is enabled:
                if Hunyuan3D mode is "OFFICIAL_API":
                    - For objects/models, do the following steps:
                        1. Create the model generation task
                            - Use generate_hunyuan3d_model by providing either a **text description** OR an **image(local or urls) reference**.
                            - Go to cloud.tencent.com out how to get their own SecretId and SecretKey
                        2. Poll the status
                            - Use poll_hunyuan_job_status() to check if the generation task has completed or failed
                        3. Import the asset
                            - Use import_generated_asset_hunyuan() to import the generated OBJ model the asset
                    if Hunyuan3D mode is "LOCAL_API":
                        - For objects/models, do the following steps:
                        1. Create the model generation task
                            - Use generate_hunyuan3d_model if image (local or urls)  or text prompt is given and import the asset

                You can reuse assets previous generated by running python code to duplicate the object, without creating another generation task.

    3. Always check the world_bounding_box for each item so that:
        - Ensure that all objects that should not be clipping are not clipping.
        - Items have right spatial relationship.
    
    4. Recommended asset source priority:
        - For specific existing objects: First try Sketchfab, then PolyHaven
        - For generic objects/furniture: First try PolyHaven, then Sketchfab
        - For custom or unique items not available in libraries: Use Hyper3D Rodin or Hunyuan3D
        - For environment lighting: Use PolyHaven HDRIs
        - For materials/textures: Use PolyHaven textures

    Only fall back to scripting when:
    - PolyHaven, Sketchfab, Hyper3D, and Hunyuan3D are all disabled
    - A simple primitive is explicitly requested
    - No suitable asset exists in any of the libraries
    - Hyper3D Rodin or Hunyuan3D failed to generate the desired asset
    - The task specifically requires a basic material/color
    """

# Main execution

def main():
    """Run the MCP server"""
    mcp.run()

if __name__ == "__main__":
    main()