.PHONY: run run-prod stop restart install clean logs help

# Default target
help:
	@echo "Available commands:"
	@echo "  make run      - Start the Streamlit app (auth bypass for localhost)"
	@echo "  make run-prod - Start the Streamlit app (with authentication required)"
	@echo "  make stop     - Stop the running app"
	@echo "  make restart  - Restart the app"
	@echo "  make install  - Install dependencies"
	@echo "  make clean    - Remove cache files"
	@echo "  make logs     - Show recent app logs"

# Activate venv and run the app (with auth bypass for localhost)
run:
	@echo "Starting Streamlit app (auth bypass enabled for localhost)..."
	@bash -c "source venv/bin/activate && BYPASS_AUTH=true streamlit run app.py --server.headless true"

# Run with authentication required (production mode)
run-prod:
	@echo "Starting Streamlit app (authentication required)..."
	@bash -c "source venv/bin/activate && streamlit run app.py --server.headless true"

# Stop the running app
stop:
	@echo "Stopping Streamlit app..."
	@pkill -f "streamlit run app.py" || true

# Restart the app
restart: stop
	@sleep 1
	@$(MAKE) run

# Install dependencies
install:
	@echo "Creating virtual environment..."
	@python3 -m venv venv
	@echo "Installing dependencies..."
	@source venv/bin/activate && pip install -r requirements.txt

# Clean cache files
clean:
	@echo "Cleaning cache files..."
	@rm -rf __pycache__ .streamlit
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "Done."

# Show logs (tail the most recent terminal output)
logs:
	@echo "Recent app output:"
	@ps aux | grep -i streamlit | grep -v grep || echo "No Streamlit process found"

