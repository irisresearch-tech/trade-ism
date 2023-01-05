import os
import time
import json
import math
import kite_connect

enctoken = os.getenv("enctoken") # set enctoken, REQUIRED field


def get_client_order_id():
    return "IRIS-{timestamp}".format(timestamp=round(time.time() * 1000))

def place_order():
    buy_order_type, sell_order_type = client.ORDER_TYPE_LIMIT, client.ORDER_TYPE_LIMIT
    expiry = os.getenv("expiry")
    if expiry == None or expiry == "":
        print("please export contract expiry for BANKNIFTY, exiting!")
        return 
    instrument_prefix = "BANKNIFTY23"+expiry
    instruments = os.getenv("instrument")
    if instruments == None or instruments == "":
        print("instrument cannot be empty, exiting!")
        return
    instruments = instruments.strip().split(",")
    if len(instruments) != 2:
        print("required 2 instruments to sell and buy, exiting!")
        return 
    
    limit_price = os.getenv("price")
    buy_limit_price, sell_limit_price = 0.0, 0.0
    if limit_price == None or limit_price.strip() == "":
        sell_order_type = client.ORDER_TYPE_MARKET
        buy_order_type = client.ORDER_TYPE_MARKET
        print("Setting order type to MARKET")
    elif limit_price.__contains__(","):
        prices = limit_price.strip().split(",")
        if prices[0] != "":
            sell_limit_price = float(prices[0])
        else:
            sell_order_type = client.ORDER_TYPE_MARKET
        if prices[1] != "":
            buy_limit_price = float(prices[1])
        else:
            buy_order_type = client.ORDER_TYPE_MARKET
    
        
    quantity = os.getenv("quantity")
    if quantity.strip() == "":
        print("quantity is required field")
        return
    if instruments[0] != "":
        total_orders_count, failed_count = place_order_kite(
            instrument=(instrument_prefix+instruments[0]).upper(),
            side=client.TRANSACTION_TYPE_SELL,
            order_type=sell_order_type,
            price=float(sell_limit_price),
            size=int(quantity),
        )
        print("SELL orders placed: %d, failed: %d" % (total_orders_count, failed_count))
        
    if instruments[1] != "":
        total_orders_count, failed_count = place_order_kite(
            instrument=(instrument_prefix+instruments[1]).upper(),
            side=client.TRANSACTION_TYPE_BUY,
            size=int(quantity),
            price=float(buy_limit_price),
            order_type=buy_order_type,
        )
        print("BUY orders placed: %d, failed: %d" % (total_orders_count, failed_count))
    print("------------------------------------------")
    print("\n")


def place_order_kite(instrument, side, order_type, price, size):
    num_orders = math.ceil(int(size) / 900)
    quantity_left = int(size)
    orders = []
    failed_count = 0
    print("%s %s, %s %s, %s"% (instrument, side, order_type, price, size))
    while num_orders > 0:
        order_size = int(min(900, quantity_left))
        num_orders-=1
        quantity_left-=order_size
        order_response = client.place_order(
            variety=client.VARIETY_REGULAR,
            product=client.PRODUCT_NRML,
            exchange=client.EXCHANGE_NFO,
            validity=client.VALIDITY_DAY,
            tradingsymbol=instrument,
            transaction_type=side,
            quantity=order_size,
            price=price,
            order_type=order_type,
            disclosed_quantity=0,
            trigger_price=0,
            squareoff=0,
            stoploss=0,
            trailing_stoploss=0,
            tag=get_client_order_id()
        )
        
        if order_response["data"] and order_response["data"]["order_id"]:
            orders.append(order_response["data"])
            print("%s order placed on instrument %s order_id %s, price: %s, size: %s, order_type: %s" % (side, instrument, order_response["data"]["order_id"], price, order_size, order_type))
        else:
            failed_count += 1
            print("failed to place order")
    return num_orders, failed_count

def close_all_positions(side):
    open_positions = get_open_positions()
    for p in open_positions:
        if side == "buy" and p['open_size'] < 0:
            continue
        elif side == "sell" and p['open_size'] > 0:
            continue
        close_side = client.TRANSACTION_TYPE_SELL if p['open_size'] > 0 else client.TRANSACTION_TYPE_BUY
        order_type = client.ORDER_TYPE_MARKET
        order_count, failed_count = place_order_kite(
            p['instrument'], side = close_side,
            order_type=order_type,
            price=0.0, size=abs(p['open_size']))
        print("%s orders placed to close position. order count: %d, failed: %d" % (close_side, order_count, failed_count))
        
def get_open_positions():
    positions_response = client.positions()
    open_positions = []
    for p in positions_response['net']:
        if p["sell_quantity"] != p["buy_quantity"]:
            open_position = {
                "instrument": p['tradingsymbol'],
                "buy_price": p['buy_price'],
                "sell_price": p['sell_price'],
                "buy_quantity": p['buy_quantity'],
                "sell_quantity": p['sell_quantity'],
                "open_size": p['buy_quantity'] - p['sell_quantity'],
            }
            open_positions.append(open_position)
    return open_positions
    
if __name__ == '__main__':
    client = kite_connect.KiteApp(enctoken=enctoken)
    command = os.getenv("command")
    if command != None :
        if command == "close_all":
            side = os.getenv("side")
            close_all_positions(side=side)
        elif command == "place_order":
            place_order()
        
    


