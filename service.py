import ccxt
import time
import json
import os
import pandas as pd
from datetime import datetime
from kivy.utils import platform

# تحديد مسار الملفات حسب النظام
if platform == 'android':
    from android.storage import app_storage_path
    DATA_DIR = app_storage_path()
else:
    DATA_DIR = "."

CONFIG_FILE = os.path.join(DATA_DIR, "bot_config.json")
LOG_FILE = os.path.join(DATA_DIR, "bot_output.log")

# دالة مخصصة للكتابة في السجلات وعرضها بالتطبيق
def dynamic_print(text):
    now = datetime.now().strftime('%H:%M:%S')
    log_entry = f"[{now}] {text}\n"
    with open(LOG_FILE, 'a') as f:
        f.write(log_entry)

# دالة لقراءة المتغيرات التي أدخلها المستخدم من الواجهة في أي وقت
def load_runtime_configs():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {
        "API_KEY": "fff9bf53",
        "SECRET_KEY": "aac",
        "COIN_QUOTE": "USDT",
        "SCREEN_REFRESH_INTERVAL": 12000,
        "AUTO_REINVEST": True
    }

# تحميل الإعدادات الأولية للتشغيل
configs = load_runtime_configs()
API_KEY = configs['API_KEY']
SECRET_KEY = configs['SECRET_KEY']
COIN_QUOTE = configs['COIN_QUOTE']
AUTO_REINVEST = configs['AUTO_REINVEST']
SCREEN_REFRESH_INTERVAL = configs['SCREEN_REFRESH_INTERVAL']

DATA_FILE = os.path.join(DATA_DIR, 'grid_bot_state.json')

TRADING_PAIRS = {
    "COIN_1": {
        "SYMBOL": "SOL/USDT",       
        "BASE": "SOL", 
        "GRID_AMOUNT_USDT": 1.9,     
        "DROP_PERCENT": 0.005,     
        "TAKE_PROFIT_PERCENT": 0.002, 
        "TIMEFRAMES_CONFIG": {"5m": {"FEE_RATE": 0.004}} 
    }
}

last_clear_time = time.time()  

# ربط محرك التداول XT.COM
exchange = ccxt.xt({
    'apiKey': API_KEY,
    'secret': SECRET_KEY,
    'enableRateLimit': True,
})

def save_state(state):
    try:
        with open(DATA_FILE, 'w') as f:
            json.dump(state, f, indent=4)
    except Exception as e:
        dynamic_print(f"❌ Error saving bot state: {e}")

def load_state():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r') as f:
                loaded = json.load(f)
                for key, config in TRADING_PAIRS.items():
                    symbol = config["SYMBOL"]
                    if symbol in loaded:
                        if "accumulated_reinvest_ratio" not in loaded[symbol]:
                            loaded[symbol]["accumulated_reinvest_ratio"] = 1.0
                        if "total_successful_trades" not in loaded[symbol]:
                            loaded[symbol]["total_successful_trades"] = 0
                        if "total_secured_profit" not in loaded[symbol]:
                            loaded[symbol]["total_secured_profit"] = 0.0
                return loaded
        except:
            pass
    
    initial_state = {}
    for key, config in TRADING_PAIRS.items():
        symbol = config["SYMBOL"]
        initial_state[symbol] = {
            "active_trades": [], 
            "accumulated_reinvest_ratio": 1.0,
            "total_successful_trades": 0,    
            "total_secured_profit": 0.0       
        }
    return initial_state

def get_indicators(symbol, timeframe):
    try:
        bars = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=20)
        df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['sma9'] = df['close'].rolling(window=9).mean()
        current_candle = df.iloc[-1]
        previous_candle = df.iloc[-2]
        return current_candle, previous_candle
    except Exception as e:
        dynamic_print(f"❌ Error fetching technical data for {symbol}: {e}")
        return None, None

def print_wallet_balance(coin_base):
    try:
        balance = exchange.fetch_balance()
        base_bal = balance.get(coin_base, {}).get('free', 0)
        quote_bal = balance.get(COIN_QUOTE, {}).get('free', 0)
        dynamic_print(f"💼 Balance | {coin_base}: {base_bal:.6f} | {COIN_QUOTE}: {quote_bal:.4f}$")
        return base_bal, quote_bal
    except Exception as e:
        dynamic_print(f"❌ Error fetching balance: {e}")
        return 0, 0

def run_bot():
    global last_clear_time, API_KEY, SECRET_KEY, COIN_QUOTE, AUTO_REINVEST, SCREEN_REFRESH_INTERVAL, exchange
    dynamic_print("🤖 XT.COM Single-Coin Grid DCA Bot Service started...")
    
    try:
        exchange.load_markets()
    except Exception as e:
        dynamic_print(f"⚠️ Warning: Could not load markets precision rules: {e}")
        
    state = load_state()
    
    state_updated = False
    for key, config in TRADING_PAIRS.items():
        symbol = config["SYMBOL"]
        if symbol not in state:
            state[symbol] = {"active_trades": [], "accumulated_reinvest_ratio": 1.0, "total_successful_trades": 0, "total_secured_profit": 0.0}
            state_updated = True
    if state_updated:
        save_state(state)
    
    while True:
        try:
            # تحديث الإعدادات ديناميكياً أثناء تشغيل الحلقة بدون الحاجة لإيقاف البوت
            current_configs = load_runtime_configs()
            AUTO_REINVEST = current_configs['AUTO_REINVEST']
            SCREEN_REFRESH_INTERVAL = current_configs['SCREEN_REFRESH_INTERVAL']
            
            # إذا قام المستخدم بتحديث المفاتيح برمجياً أثناء عمل الخدمة
            if current_configs['API_KEY'] != API_KEY or current_configs['SECRET_KEY'] != SECRET_KEY:
                API_KEY = current_configs['API_KEY']
                SECRET_KEY = current_configs['SECRET_KEY']
                exchange = ccxt.xt({'apiKey': API_KEY, 'secret': SECRET_KEY, 'enableRateLimit': True})

            if time.time() - last_clear_time >= SCREEN_REFRESH_INTERVAL:
                # في الأندرويد، نقوم بمسح ملف السجل لتجنب امتلاء الذاكرة
                if os.path.exists(LOG_FILE):
                    os.remove(LOG_FILE)
                last_clear_time = time.time()

            for key, config in TRADING_PAIRS.items():
                SYMBOL = config["SYMBOL"]
                COIN_BASE = config["BASE"]
                GRID_AMOUNT = config["GRID_AMOUNT_USDT"]
                DROP_P = config["DROP_PERCENT"]
                TP_P = config["TAKE_PROFIT_PERCENT"]
                
                for TIMEFRAME, tf_settings in config["TIMEFRAMES_CONFIG"].items():
                    CURRENT_FEE_RATE = tf_settings["FEE_RATE"]
                    
                    current_candle, previous_candle = get_indicators(SYMBOL, TIMEFRAME)
                    if current_candle is None or previous_candle is None:
                        continue
                    
                    current_price = current_candle['close']
                    open_price = current_candle['open']
                    sma_current = current_candle['sma9']
                    prev_price = previous_candle['close']
                    sma_prev = previous_candle['sma9']
                    
                    active_trades = state[SYMBOL]["active_trades"]
                    levels_count = len(active_trades)
                    
                    total_trades = state[SYMBOL].get("total_successful_trades", 0)
                    total_profit = state[SYMBOL].get("total_secured_profit", 0.0)
                    
                    if AUTO_REINVEST:
                        current_ratio = state[SYMBOL].get("accumulated_reinvest_ratio", 1.0)
                        actual_grid_amount = GRID_AMOUNT * current_ratio
                    else:
                        actual_grid_amount = GRID_AMOUNT
                    
                    reinvest_status_str = f" | Reinvest: ON (x{state[SYMBOL].get('accumulated_reinvest_ratio', 1.0):.3f})" if AUTO_REINVEST else ""
                    dynamic_print(f"🔄 {SYMBOL} | Price: {current_price} | SMA-9: {sma_current:.2f} | Active Levels: {levels_count} | Total Trades: {total_trades} | Total Profit: {total_profit:.4f}$ | Status: {'HOLDING & DCA' if levels_count > 0 else 'IDLE'}{reinvest_status_str}")
                    
                    # ----------------------------------------------------
                    # LOGIC 1: BUY LEVEL INITIAL OR DCA GRID ENTRY
                    # ----------------------------------------------------
                    can_buy = False
                    reason = ""
                    
                    if levels_count == 0:
                        if (prev_price < sma_prev) and (current_price > sma_current) and (current_price > open_price):
                            can_buy = True
                            reason = "Initial Grid Level 1 (Indicator Trigger)"
                    else:
                        last_buy_price = active_trades[-1]["buy_price"]
                        target_dca_price = last_buy_price * (1 - DROP_P)
                        
                        if current_price <= target_dca_price:
                            can_buy = True
                            reason = f"DCA Grid Level {levels_count + 1} (Price dropped {DROP_P*100}% below last buy {last_buy_price})"
                    
                    if can_buy:
                        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        dynamic_print(f"🟢 [BUY TRIGGER] {SYMBOL} -> Reason: {reason} | Size: ${actual_grid_amount:.2f}")
                        _, usd_balance = print_wallet_balance(COIN_BASE)
                        
                        if usd_balance < actual_grid_amount:
                            dynamic_print(f"❌ Aborted: Insufficient USDT balance ({usd_balance:.4f}$). Needs {actual_grid_amount}$.")
                            continue
                            
                        try:
                            exchange.options['createMarketBuyOrderRequiresPrice'] = False
                            order = exchange.create_market_buy_order(SYMBOL, actual_grid_amount)
                            
                            time.sleep(2) 
                            actual_wallet_bal, _ = print_wallet_balance(COIN_BASE)
                            adjusted_amount = actual_wallet_bal * (1 - 0.00005)
                            final_precision_amount = float(exchange.amount_to_precision(SYMBOL, adjusted_amount))

                            new_level = {
                                "level_id": len(active_trades) + 1,
                                "order_id": order.get('id', 'MANUAL_ID'),
                                "buy_price": order.get('average', current_price) if order.get('average') else current_price,
                                "amount_bought": final_precision_amount, 
                                "total_cost_usd": order.get('cost', actual_grid_amount) if order.get('cost') else actual_grid_amount
                            }
                            
                            state[SYMBOL]["active_trades"].append(new_level)
                            save_state(state)
                            
                            dynamic_print(f"🛒 Successfully Opened Level {new_level['level_id']} at price {new_level['buy_price']}")
                            time.sleep(5)
                        except Exception as e:
                            dynamic_print(f"❌ Execution Buy Error: {e}")

                    # ----------------------------------------------------
                    # LOGIC 2: INDEPENDENT SELL CHECK FOR EACH ACTIVE LEVEL
                    # ----------------------------------------------------
                    if levels_count > 0:
                        sell_signal = (prev_price >= sma_prev) and (current_price < sma_current)

                        for level in list(active_trades):
                            stored_buy_price = level["buy_price"]
                            min_sell_target = stored_buy_price * (1 + TP_P + CURRENT_FEE_RATE)
                            
                            if current_price >= min_sell_target and not sell_signal:
                                current_gain = ((current_price - stored_buy_price) / stored_buy_price) * 100
                                dynamic_print(f"✨ [PROFIT TARGET MET] Level {level['level_id']} | Gain: +{current_gain:.2f}% | Waiting for SMA-9 Signal...")
                            
                            if current_price >= min_sell_target and sell_signal:
                                dynamic_print(f"🔴 [PROFIT & SIGNAL MET] Level {level['level_id']} for {SYMBOL} Executing Sell...")
                                
                                try:
                                    raw_amount = level["amount_bought"]
                                    stored_cost = level.get("total_cost_usd", GRID_AMOUNT)
                                    
                                    if not raw_amount or raw_amount == "None" or raw_amount == 0:
                                        actual_coin_bal, _ = print_wallet_balance(COIN_BASE)
                                        raw_amount = actual_coin_bal * (1 - 0.00005)
                                        
                                    if float(raw_amount) > 0:
                                        amount_to_sell = exchange.amount_to_precision(SYMBOL, raw_amount)
                                        order = exchange.create_market_sell_order(SYMBOL, amount_to_sell)
                                        
                                        approx_sell_return = float(amount_to_sell) * current_price
                                        trade_profit_usd = approx_sell_return - stored_cost
                                        if trade_profit_usd < 0:
                                            trade_profit_usd = stored_cost * TP_P

                                        state[SYMBOL]["total_successful_trades"] = state[SYMBOL].get("total_successful_trades", 0) + 1
                                        state[SYMBOL]["total_secured_profit"] = state[SYMBOL].get("total_secured_profit", 0.0) + trade_profit_usd

                                        level_gain_ratio = current_price / stored_buy_price
                                        if AUTO_REINVEST and level_gain_ratio > 1.0:
                                            state[SYMBOL]["accumulated_reinvest_ratio"] = state[SYMBOL].get("accumulated_reinvest_ratio", 1.0) * level_gain_ratio
                                        
                                        dynamic_print(f"💰 SUCCESS: Sold Level {level['level_id']} at {current_price}$")
                                        
                                        state[SYMBOL]["active_trades"].remove(level)
                                        save_state(state)
                                        time.sleep(5)
                                        break 
                                    else:
                                        dynamic_print("❌ Sell aborted: Free wallet balance for level is 0.")
                                except Exception as e:
                                    dynamic_print(f"❌ Execution Sell Error for Level {level['level_id']}: {e}")

                if time.time() % 60 < 10:
                    print_wallet_balance(COIN_BASE)

        except Exception as e:
            dynamic_print(f"❌ Unexpected error in grid loop: {e}")
            
        time.sleep(5) 

if __name__ == "__main__":
    run_bot()
