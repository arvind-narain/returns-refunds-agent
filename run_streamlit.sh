#!/bin/bash
# Script to run the Streamlit app

echo "=================================="
echo "Returns Assistant - Streamlit App"
echo "=================================="
echo ""

# Check if streamlit is installed
if ! command -v streamlit &> /dev/null
then
    echo "⚠️  Streamlit not found. Installing dependencies..."
    pip install -r requirements_streamlit.txt
    echo ""
fi

echo "🚀 Starting Streamlit app..."
echo ""
echo "The app will open in your browser at: http://localhost:8501"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

streamlit run streamlit_app.py
