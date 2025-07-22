#!/usr/bin/env python3
"""
Start NYX FastAPI Development Server

This script starts the NYX FastAPI application for development and testing.
"""

import sys
import os
import uvicorn

# Add current directory to Python path
sys.path.insert(0, os.path.abspath('.'))

def main():
    """Start the FastAPI development server"""
    print("🚀 Starting NYX FastAPI Development Server")
    print("=" * 50)
    print("📍 API Documentation: http://localhost:8000/docs")
    print("📍 ReDoc Documentation: http://localhost:8000/redoc")
    print("🏥 Health Check: http://localhost:8000/health")
    print("🔍 System Status: http://localhost:8000/api/v1/system/status")
    print("=" * 50)
    
    try:
        uvicorn.run(
            "app.main:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
            log_level="info",
            access_log=True
        )
    except KeyboardInterrupt:
        print("\n👋 NYX FastAPI server stopped")

if __name__ == "__main__":
    main()