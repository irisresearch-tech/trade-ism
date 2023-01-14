import os
import time
import json
import math
import kite_connect
import sys
from time import sleep
from operator import itemgetter
from signal import signal, SIGPIPE, SIG_DFL

enctoken = os.getenv("enctoken") # set enctoken, REQUIRED field
def myprint(*args):
    debug = "1"
    if(debug == "1"):
        for arg in args:
            print(arg)
                            

def get_client_order_id():
    return "IRIS-{timestamp}".format(timestamp=round(time.time() * 1000))

def place_order():
    buy_order_type, sell_order_type = client.ORDER_TYPE_LIMIT, client.ORDER_TYPE_LIMIT
    expiry = os.getenv("expiry")
    if expiry == None or expiry == "":
        myprint("please export contract expiry for BANKNIFTY, exiting!")
        return 
    instrument_prefix = "BANKNIFTY23"+expiry
    instruments = os.getenv("instrument")
    if instruments == None or instruments == "":
        myprint("instrument cannot be empty, exiting!")
        return
    instruments = instruments.strip().split(",")
    if len(instruments) != 2:
        myprint("required 2 instruments to sell and buy, exiting!")
        return 
    
    limit_price = os.getenv("price")
    buy_limit_price, sell_limit_price = 0.0, 0.0
    if limit_price == None or limit_price.strip() == "":
        sell_order_type = client.ORDER_TYPE_MARKET
        buy_order_type = client.ORDER_TYPE_MARKET
        myprint("Setting order type to MARKET")
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
        myprint("quantity is required field")
        return
    if instruments[0] != "":
        total_orders_count, failed_count = place_order_kite(
            instrument=(instrument_prefix+instruments[0]).upper(),
            side=client.TRANSACTION_TYPE_SELL,
            order_type=sell_order_type,
            price=float(sell_limit_price),
            size=int(quantity),
        )
        myprint("SELL orders placed: %d, failed: %d" % (total_orders_count, failed_count))
        
    if instruments[1] != "":
        total_orders_count, failed_count = place_order_kite(
            instrument=(instrument_prefix+instruments[1]).upper(),
            side=client.TRANSACTION_TYPE_BUY,
            size=int(quantity),
            price=float(buy_limit_price),
            order_type=buy_order_type,
        )
        myprint("BUY orders placed: %d, failed: %d" % (total_orders_count, failed_count))
    myprint("------------------------------------------")
    myprint("\n")


def place_order_kite(instrument, side, order_type, price, size):
    num_orders = math.ceil(int(size) / 900)
    quantity_left = int(size)
    orders = []
    failed_count = 0
    myprint("%s %s, %s %s, %s"% (instrument, side, order_type, price, size))
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
            myprint("%s order placed on instrument %s order_id %s, price: %s, size: %s, order_type: %s" % (side, instrument, order_response["data"]["order_id"], price, order_size, order_type))
        else:
            failed_count += 1
            myprint("failed to place order")
    return num_orders, failed_count


def close_all_positions(side):
    open_positions = get_open_positions()
    for p in open_positions:
        if side == "buy" and p['open_size'] < 0:
            continue
        elif side == "sell" and p['open_size'] > 0:
            continue
        elif side == "PE" and "CE" in p['instrument']:
            continue
        elif side == "CE" and "PE" in p['instrument']:
            continue
        elif side == "PEsell" and ("CE" in p['instrument'] or p['open_size'] > 0):
            continue
        elif side == "CEsell" and ("PE" in p['instrument'] or p['open_size'] > 0):
            continue
        close_side = client.TRANSACTION_TYPE_SELL if p['open_size'] > 0 else client.TRANSACTION_TYPE_BUY
        order_type = client.ORDER_TYPE_MARKET
        order_count, failed_count = place_order_kite(
            p['instrument'], side = close_side,
            order_type=order_type,
            price=0.0, size=abs(p['open_size']))
        myprint("%s orders placed to close position. order count: %d, failed: %d" % (close_side, order_count, failed_count))
        
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
                "side": "buy" if p['buy_quantity'] > p['sell_quantity'] else "sell",
                'pnl': p['m2m'],
            }
            open_positions.append(open_position)
    open_positions = sorted(open_positions, key=itemgetter('side'), reverse=True)
    return open_positions

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
                "side": "buy" if p['buy_quantity'] > p['sell_quantity'] else "sell",
                'pnl': p['pnl'],
            }
            open_positions.append(open_position)
    open_positions = sorted(open_positions, key=itemgetter('side'), reverse=True)
    return open_positions

def get_net_pnl(client):
    positions = client.positions()
    # print(json.dumps(positions, indent=4))
    m2m =  sum(map(
        lambda p: p["m2m"], positions["net"]
    ))
    pnl =  sum(map(
        lambda p: p["value"], positions["net"]
    ))
    unl =  sum(map(
        lambda p: p["unrealised"], positions["net"]
    ))
    print("m2m %f"%m2m)
    print("value %f"%pnl)
    print("upl %f"%unl)
    print("DONEDONECONE================================================= ")
    return sum(map(
        lambda p: p["pnl"], positions["net"]
    ))
    
def stop_loss_runner(sl_amount):
    while True:
        client = kite_connect.KiteApp(enctoken=enctoken)
        net_pnl = get_net_pnl(client)
        myprint("Net PnL: %f" % net_pnl)
        if net_pnl < sl_amount:
            myprint("Current PnL less than SL amount: %s, closing all positions" % sl_amount)
            close_all_positions("")
        time.sleep(5)

def main():
    command = os.getenv("command")
    global debug
    debug = os.getenv("debug") # debug 
    if command != None and command != "":
        if command == "close_all":
            side = os.getenv("side")
            close_all_positions(side=side)
        elif command == "place_order":
            place_order()
        elif command == "sl_runner":
            sl_amount = os.getenv("sl_amount")
            if sl_amount != None and sl_amount != "":
                sl_amount = float(sl_amount.strip())
                stop_loss_runner(sl_amount)
            else:
                myprint("required sl_amount. Exiting!")
        else:
            myprint("%s command not implemented" % command)
    else:
        myprint("required command. Exiting!")



    
if __name__ == '__main__':
    client = kite_connect.KiteApp(enctoken=enctoken)
    main()
