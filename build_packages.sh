#!/bin/bash

# Update pip
pip install --upgrade pip setuptools wheel

# Install packages one by one to catch any issues
pip install Flask==2.0.1
pip install Werkzeug==2.0.1 
pip install Jinja2==3.0.1
pip install gunicorn==20.1.0
pip install python-dotenv==0.19.0
pip install requests==2.26.0

# Install yfinance with minimal dependencies
pip install numpy==1.21.2
pip install pandas==1.3.3
pip install multitasking==0.0.11
pip install lxml==4.6.3
pip install yfinance==0.2.18 --no-deps
pip install appdirs
pip install frozendict
pip install pytz

# Print package sizes to debug
echo "Package sizes:"
pip list --format=freeze | awk -F== '{print $1}' | xargs -I{} du -sh $(pip show {} | grep Location | awk '{print $2}')/{}

echo "Installation completed" 