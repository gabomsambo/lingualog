"""
Server run script for LinguaLog.

This script handles starting the FastAPI server with the correct module path.
"""
import uvicorn

if __name__ == "__main__":
    uvicorn.run("backend.server:app", host="0.0.0.0", port=8000, reload=True) 