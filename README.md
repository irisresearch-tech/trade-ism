

# Set enc token
export enctoken=""

# Set expiry
export expiry="105"
# close all positons, use side as a filter
command=close_all side=sell python kite_runner.py

# place new orders
command=place_order price=5,5, quantity=100 instrument=43000PE,42000PE python kite_runner.py
