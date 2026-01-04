from fastmcp import FastMCP
import os
import math

# Initialize the Server
mcp = FastMCP("Local Agent Tools")

@mcp.tool()
def list_directory() -> str:
    """Lists all files and folders in the current directory."""
    try:
        files = os.listdir(".")
        return ", ".join(files) if files else "Directory is empty."
    except Exception as e:
        return f"Error listing directory: {e}"

@mcp.tool()
def check_file_exists(filename: str) -> str:
    """Checks if a file exists in the current directory."""
    # Security Checks
    if ".." in filename or filename.startswith(("/", "\\")) or ":" in filename:
         return "Error: Access denied. Directory traversal detected."
    
    try:
        exists = os.path.exists(filename)
        return f"File '{filename}' exists: {exists}"
    except Exception as e:
        return f"Error: {e}"

@mcp.tool()
def calculator(expression: str) -> str:
    """Calculates a math expression. Supports basic math and functions like log, sqrt."""
    # Allow letters for functions (log, sqrt) and commas
    allowed_chars = set("0123456789+-*/()., abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ")
    
    if not set(expression).issubset(allowed_chars):
        return "Error: Invalid characters. Only math expressions allowed."
    
    try:
        safe_math = {k: v for k, v in math.__dict__.items() if not k.startswith("__")}
        result = eval(expression, {"__builtins__": None}, safe_math)
        return str(result)
    except Exception as e:
        return f"Error evaluating expression: {e}"

if __name__ == "__main__":
    mcp.run()