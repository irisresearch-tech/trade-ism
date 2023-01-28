import os
import time
import json
import math
import kite_connect
import sys
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

def straddle_order():

    expiry = os.getenv("expiry")
    if expiry == None or expiry == "":
        myprint("please export contract expiry for BANKNIFTY, exiting!")
        return 

    instrument1 = os.getenv("inst1")
    instrument2 = os.getenv("inst2")
    if((instrument1 == None or instrument1 == "") or (instrument2 == None or instrument2 == "")):
        myprint("any of instruments cannot be empty, exiting!")
        return

    order_side = os.getenv("side")

    if(os.getenv("side") == "sell"):
        order_side = client.TRANSACTION_TYPE_SELL
    elif(os.getenv("side") == "buy"):
        order_side = client.TRANSACTION_TYPE_BUY
    else:
        myprint("side can be either buy or sell nothing else, exiting!")
        return


    instrument_prefix = "BANKNIFTY23"+expiry

    limit_price = 0.0
    order_type = client.ORDER_TYPE_MARKET

    quantity = os.getenv("quantity")
    if quantity == None or quantity == "":
        myprint("quantity is required field")
        return

    size = int(quantity.strip())
    num_orders = math.ceil(int(size) / 900)
    quantity_left = int(size)

    while num_orders > 0:
        order_size = int(min(900, quantity_left))
        num_orders-=1
        quantity_left-=order_size

        total_orders_count, failed_count = place_order_kite(
            instrument=(instrument_prefix+instrument1).upper(),
            side=order_side,
            order_type=order_type,
            price=float(limit_price),
            size=order_size,
        )
        myprint("orders placed for instrument 1: %d, failed: %d" % (total_orders_count, failed_count))
        
        total_orders_count, failed_count = place_order_kite(
            instrument=(instrument_prefix+instrument2).upper(),
            side=order_side,
            order_type=order_type,
            price=float(limit_price),
            size=order_size,
        )
        myprint("orders placed for instrument 2: %d, failed: %d" % (total_orders_count, failed_count))
    myprint("------------------------------------------")
    myprint("\n")

def place_order():
    buy_order_type, sell_order_type = client.ORDER_TYPE_LIMIT, client.ORDER_TYPE_LIMIT
    expiry = os.getenv("expiry")
    if expiry == None or expiry == "":
        myprint("please export contract expiry for BANKNIFTY, exiting!")
        return 
    buy_instrument = os.getenv("Binstrument")
    sell_instrument = os.getenv("Sinstrument")
    if((buy_instrument == None or buy_instrument == "") and (sell_instrument == None or sell_instrument == "")):
        myprint("Bothinstrumentis cannot be empty, exiting!")
        return

    instrument_prefix = "BANKNIFTY23"+expiry

    buy_limit_price, sell_limit_price = 0.0, 0.0


    buy_price = os.getenv("Bprice")
    sell_price = os.getenv("Sprice")

    if(buy_price == None or buy_price == ""):
        buy_order_type = client.ORDER_TYPE_MARKET
        buy_limit_price = 0
    else:
        buy_limit_price = float(buy_price.strip())

    if(sell_price == None or sell_price == ""):
        sell_order_type = client.ORDER_TYPE_MARKET
        sell_limit_price = 0
    else:
        sell_limit_price = float(sell_price.strip())
        
    quantity = os.getenv("quantity")
    if quantity == None or quantity == "":
        myprint("quantity is required field")
        return

    size = int(quantity.strip())
    num_orders = math.ceil(int(size) / 900)
    quantity_left = int(size)
    while num_orders > 0:
        order_size = int(min(900, quantity_left))
        num_orders-=1
        quantity_left-=order_size

        if sell_instrument != "" and sell_instrument != None:
            total_orders_count, failed_count = place_order_kite(
                instrument=(instrument_prefix+sell_instrument).upper(),
                side=client.TRANSACTION_TYPE_SELL,
                order_type=sell_order_type,
                price=float(sell_limit_price),
                size=order_size,
            )
            myprint("SELL orders placed: %d, failed: %d" % (total_orders_count, failed_count))
        
        if buy_instrument != "" and buy_instrument != None:
            total_orders_count, failed_count = place_order_kite(
                instrument=(instrument_prefix+buy_instrument).upper(),
                side=client.TRANSACTION_TYPE_BUY,
                size=order_size,
                price=float(buy_limit_price),
                order_type=buy_order_type,
            )
            myprint("BUY orders placed: %d, failed: %d" % (total_orders_count, failed_count))
    myprint("------------------------------------------")
    myprint("\n")


def place_order_kite(instrument, side, order_type, price, size):

    if "BANK" in instrument:
        single_max_order_size = 900
    else:
        single_max_order_size = 1800
    num_orders = math.ceil(int(size) / single_max_order_size)
    quantity_left = int(size)
    orders = []
    failed_count = 0
    myprint("%s %s, %s %s, %s"% (instrument, side, order_type, price, size))
    while num_orders > 0:
        order_size = int(min(single_max_order_size, quantity_left))
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


def close_all_positions(positions, side):
    open_positions = get_open_positions(positions)
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
        print("######### Closing position in %s" % p["instrument"])
        print(json.dumps(p, indent=4))
        close_side = client.TRANSACTION_TYPE_SELL if p['open_size'] > 0 else client.TRANSACTION_TYPE_BUY
        order_type = client.ORDER_TYPE_MARKET
        order_count, failed_count = place_order_kite(
            p['instrument'], side = close_side,
            order_type=order_type,
            price=0.0, size=abs(p['open_size']))
        myprint("%s orders placed to close position. order count: %d, failed: %d" % (close_side, order_count, failed_count))
        
def pnl(entry_price, exit_price, size, side):
    if side == "buy":
        return (exit_price-entry_price)*size
    return (entry_price - exit_price)*size

def prepare_position_info(position_data, last_price):
    position = {
        "instrument": position_data["tradingsymbol"],
        "entry_price": position_data["buy_price"] if position_data['buy_quantity'] > position_data['sell_quantity'] else position_data["sell_price"],
        "exit_price": position_data["sell_price"] if position_data['buy_quantity'] > position_data['sell_quantity'] else position_data["buy_price"],
        "side": "buy" if position_data['buy_quantity'] > position_data['sell_quantity'] else "sell",
        "rpl": 0,
        "upl": 0,
        "open_size": position_data["quantity"],
        "last_price": last_price
    }
    if position_data["sell_quantity"] > 0 and position_data["buy_quantity"] > 0:
        position["rpl"] =  pnl(
            float(position_data['buy_price']), 
            float(position_data['sell_price']), 
            abs(min(float(position_data['buy_quantity']), float(position_data['sell_quantity']))), 
            "buy"
        ) 
    position["upl"] = pnl(
        position_data['entry_price'], 
        last_price, abs(position_data['quantity']), 
        side=position["side"])
    return position
    

def get_open_positions(positions):
    return list(filter(
        lambda p: p["open_size"] != 0, positions
    ))

def get_todays_position_info():
    positions_data = client.positions()
    print(positions_data)
    positions = []
    
    ltp_data = client.ltp(list(map(lambda i: "NFO:"+i['tradingsymbol'], positions_data["net"])))
    for p in positions_data["net"]:
        trading_symbol = "NFO:"+p["tradingsymbol"]
        if  trading_symbol not in ltp_data and p["quantity"] != 0:
            print("failed to get ltp for %s, will fail to calculate unrealised pnl" % p["tradingsymbol"])
            continue
        positions.append(prepare_position_info(p, ltp_data[trading_symbol]["last_price"])) 
    return positions
    
def stop_loss_runner(sl_amount):
    while True:
        positions = get_todays_position_info()
        net_pnl = sum(map(
            lambda p: p["upl"]+p["rpl"], positions
        ))
        
        myprint("Net PnL: %f" % net_pnl)
        if net_pnl < sl_amount:
            myprint("Stop limit reached. stop loss amount: %s, net pnl: %s, closing all positions" % (sl_amount, net_pnl))
            close_all_positions(positions, "")
        time.sleep(5)

def main():
    command = os.getenv("command")
    global debug
    debug = os.getenv("debug") # debug 
    if command != None and command != "":
        if command == "close_all":
            side = os.getenv("side")
            positions = get_todays_position_info()
            close_all_positions(positions, side=side)
        elif command == "place_order":
            place_order()
        elif command == "straddle":
            straddle_order()
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