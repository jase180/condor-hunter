#!/bin/bash
# Launch the Iron Condor Screener Streamlit app

echo "🦅 Starting Iron Condor Screener GUI..."
echo ""
echo "The app will open in your browser at http://localhost:8501"
echo "Press Ctrl+C to stop the server"
echo ""

# Run streamlit (check if it's in PATH, otherwise use full path)
if command -v streamlit &> /dev/null; then
    streamlit run app.py
else
    # Try user-local bin
    ~/.local/bin/streamlit run app.py
fi
