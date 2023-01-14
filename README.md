

# Set enc token
export enctoken=""

# Set expiry
export expiry="105"

# close all positons, use side as a filter
command=close_all side=sell python kite_runner.py

# place new orders
command=place_order price=5,5, quantity=100 instrument=43000PE,42000PE python kite_runner.py

# SL runner: this script will run every 10 seconds, PRESS CTRL + C to stop script
command=sl_runner sl_amount=-2000 python kite_runner.py

# to remove all git local changes
git checkout .

# pull latest code from msater branch
git pull origin master
