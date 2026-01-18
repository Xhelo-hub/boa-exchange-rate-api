"""
Simple server starter for local development
"""
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

print("=" * 60)
print("Starting BoA Exchange Rate API")
print("=" * 60)
print(f"Project root: {PROJECT_ROOT}")
print("Server will be available at: http://localhost:8000")
print("API docs: http://localhost:8000/docs")
print("Protected endpoints require X-API-Key header")
print("\nPress Ctrl+C to stop\n")

if __name__ == "__main__":
    # Start uvicorn without reload (causes issues with spaces in path)
    import uvicorn
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,  # Disabled due to Windows path issues
        log_level="info"
    )
