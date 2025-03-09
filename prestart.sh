#!/bin/bash
# Run NLTK downloads
python -c "import nltk; nltk.download('punkt'); nltk.download('punkt_tab')"

# Start the application
exec "$@"