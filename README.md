# Start
sudo systemctl start nginx
sudo venv/bin/python -m gunicorn --bind 127.0.0.1:5000 'server:create_app()'

# Stop
ps aux | grep python  # get pid
sudo kill {pid}
sudo venv/bin/python off.py

TODO
- Convert configuration to TOML or equivalent