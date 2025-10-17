import MetaTrader5 as mt5
from typing import Callable, TypeVar, ParamSpec, Literal
import datetime as dt
from operator import itemgetter
from third_party.candlestic.chart import Chart
from third_party.candlestic.symbol import Symbol
from third_party.candlestic.time_frame import TimeFrame
from third_party.mt5_overhead.exception import MetaTraderIOException
from third_party.mt5_overhead.mt5_result import LastErrorResult, Mt5Result, LastTickResult
from third_party.mt5_overhead.ordertype import OrderType
import warnings
import logging

P = ParamSpec("P")
T = TypeVar("T")

def mt5_last_error() -> LastErrorResult:
    lasterror = mt5.last_error()
    result = LastErrorResult(
        message=lasterror[1],
        result_code=lasterror[0],
    )
    logging.info(f"MT5 Response: {str(result)}")
    return result


def mt5_initialize_decor(func: Callable[P, Mt5Result[T | None]]) -> Callable[..., Mt5Result[T | None]]:
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> Mt5Result[T | None]:
        init_result = mt5.initialize()
        logging.info(f"MT5 Initialize: {str(init_result)}")

        if not init_result:
            _last_error = mt5_last_error()
            return Mt5Result(
                has_error=True,
                message=_last_error.message,
                result_code=_last_error.result_code,
                result=None,
            )

        try:
            result = func(*args, **kwargs)

            return result
        except MetaTraderIOException as e:
            _last_error = mt5_last_error()
            return Mt5Result(
                has_error=True,
                message=f" mt5 msg :{_last_error.message} , exception : {str(e)}",
                result_code=_last_error.result_code,
                result=None,
            )

    return wrapper


@mt5_initialize_decor
def mt5_copy_rates_range(
        symbol: Symbol,
        timeframe: TimeFrame,
        date_from: dt.datetime,
        date_to: dt.datetime,
        date_to_le: bool = False,
        date_from_gt: bool = False,
) -> Mt5Result[Chart | None]:
    if date_to_le:
        date_to = date_to + dt.timedelta(minutes=timeframe.included_m1)

    if date_from_gt:
        date_from = date_to + dt.timedelta(minutes=timeframe.included_m1)

    result = mt5.copy_rates_range(
        symbol.symbol_fullname,
        timeframe.mt5_value,
        date_from,
        date_to,
    )

    _last_error = mt5_last_error()
    if result is None and _last_error.result_code != 1:
        raise MetaTraderIOException(message=_last_error.message, code=_last_error.result_code, )

    return Mt5Result(
        has_error=_last_error.has_error,
        message=_last_error.message,
        result_code=_last_error.result_code,
        result=Chart.from_mt5_data(result, timeframe),
    )


@mt5_initialize_decor
def mt5_copy_rates_from_pos(
        symbol: Symbol,
        timeframe: TimeFrame,
        pos: int = 0,
        count: int = 100,
) -> Mt5Result[Chart | None]:
    result = mt5.copy_rates_from_pos(
        symbol.symbol_name,
        timeframe.mt5_value,
        pos,
        count
    )

    _last_error = mt5_last_error()
    if result is None and _last_error.result_code != 1:
        raise MetaTraderIOException(message=_last_error.message, code=_last_error.result_code, )

    return Mt5Result(
        has_error=_last_error.has_error,
        message=_last_error.message,
        result_code=_last_error.result_code,
        result=Chart.from_mt5_data(result, timeframe),
    )


@mt5_initialize_decor
def mt5_copy_rates_from(
        symbol: Symbol,
        timeframe: TimeFrame,
        date_from: dt.datetime,
        count: int,
) -> Mt5Result[Chart | None]:
    result = mt5.copy_rates_from(
        symbol.symbol_name,
        timeframe.mt5_value,
        date_from,
        count
    )

    _last_error = mt5_last_error()
    if result is None and _last_error.result_code != 1:
        raise MetaTraderIOException(message=_last_error.message, code=_last_error.result_code, )

    return Mt5Result(
        has_error=_last_error.has_error,
        message=_last_error.message,
        result_code=_last_error.result_code,
        result=Chart.from_mt5_data(result, timeframe),
    )

@mt5_initialize_decor
def get_symbol_current_price(symbol: Symbol) -> Mt5Result[LastTickResult]:
    result = mt5.symbol_info_tick(symbol.symbol_fullname)
    _last_error = mt5_last_error()

    bid = itemgetter(1)
    ask = itemgetter(2)

    last_tick_result = LastTickResult(
        bid=bid(result),
        ask=ask(result)
    )

    return Mt5Result(
        has_error=_last_error.has_error,
        message=_last_error.message,
        result_code=_last_error.result_code,
        result=last_tick_result
    )

@mt5_initialize_decor
def base_set_order(
        order_type: OrderType,
        symbol: Symbol,
        volume: float,
        deviation : int = 10,
        mt5_type_time : int =  mt5.ORDER_TIME_GTC,
        mt5_type_filling : int =  mt5.ORDER_FILLING_RETURN,
        entry_price: float | None = None,
        stop_loss: float | None = None,
        take_profit: float | None = None,
        external_id: str | None = None,
        magic: int | None = None,
        comment: str | None = None,

) -> Mt5Result[mt5.OrderSendResult]:

    request = {
        "action": order_type.mt5_action,
        "symbol": symbol.symbol_fullname,
        "volume": volume,
        "type": order_type.mt5_type,
        "deviation": deviation,
        "type_time":mt5_type_time,
        "type_filling": mt5_type_filling,
    }

    if entry_price is not None:
        request['price'] = entry_price

    if entry_price is not None:
        request['sl'] = stop_loss
    else:
        warnings.warn("the Stop Loss is None it can be dangerous !!!")

    if entry_price is not None:
        request['tp'] = take_profit

    if external_id is not None:
        request['retcode_external'] = external_id

    if external_id is not None:
        request['magic'] = magic

    if external_id is not None:
        request['comment'] = comment

    order_send_result: mt5.OrderSendResult = mt5.order_send(request)

    if order_send_result.retcode != 10009:
        return Mt5Result(
            has_error=True,
            message=order_send_result.comment,
            result_code=order_send_result.retcode,
            result=order_send_result,
        )

    lasterror = mt5_last_error()
    return Mt5Result(
        has_error=lasterror.has_error,
        message=lasterror.message,
        result_code=lasterror.result_code,
        result=order_send_result,
    )

@mt5_initialize_decor
def set_pending_order(
        order_type: OrderType,
        symbol: Symbol,
        volume: float,
        entry_price: float,
        stop_loss: float,
        take_profit: float,
        external_id: str | None = None,
        magic: int | None = None,
        comment: str | None = None,
) -> Mt5Result[mt5.OrderSendResult]:

    return base_set_order(
        order_type = order_type,
        symbol = symbol ,
        volume = volume ,
        mt5_type_time = mt5.ORDER_TIME_GTC,
        mt5_type_filling = mt5.ORDER_FILLING_RETURN,
        entry_price = entry_price,
        stop_loss = stop_loss ,
        take_profit =  take_profit,
        external_id =  external_id,
        magic =  magic,
        comment =  comment,
    )


@mt5_initialize_decor
def market_order(
        order_type: OrderType,
        symbol: Symbol,
        volume: float,
        stop_loss: float,
        take_profit: float,
        external_id: str | None = None,
        magic: int | None = None,
        comment: str | None = None,
) -> Mt5Result[mt5.OrderSendResult]:

    return base_set_order(
        order_type=order_type,
        symbol=symbol,
        volume=volume,
        mt5_type_time=mt5.ORDER_TIME_GTC,
        mt5_type_filling= mt5.ORDER_FILLING_FOK,
        stop_loss=stop_loss,
        take_profit=take_profit,
        external_id=external_id,
        magic=magic,
        comment=comment,
    )

@mt5_initialize_decor
def get_account_info() -> Mt5Result[mt5.AccountInfo]:
    info = mt5.account_info()

    lasterror = mt5_last_error()
    return Mt5Result(
        has_error=lasterror.has_error,
        message=lasterror.message,
        result_code=lasterror.result_code,
        result=info,
    )


@mt5_initialize_decor
def get_orders() -> Mt5Result[list[mt5.TradeOrder]]:
    orders = mt5.orders_get()
    lasterror = mt5_last_error()
    return Mt5Result(
        has_error=lasterror.result_code != 1,
        result_code=lasterror.result_code,
        message=lasterror.message,
        result=orders
    )


@mt5_initialize_decor
def get_positions() -> Mt5Result[list[mt5.TradePosition]]:
    positions = mt5.positions_get()
    lasterror = mt5_last_error()

    return Mt5Result(
        has_error=lasterror.result_code != 1,
        result_code=lasterror.result_code,
        message=lasterror.message,
        result=positions
    )


@mt5_initialize_decor
def get_deals_history(
        from_date: dt.datetime = dt.datetime.now(dt.UTC) - dt.timedelta(days=365),
        to_date: dt.datetime = dt.datetime.now(dt.UTC) + dt.timedelta(days=1)
) -> Mt5Result[list[mt5.TradeDeal]]:
    deals = mt5.history_deals_get(from_date, to_date)

    lasterror = mt5_last_error()

    return Mt5Result(
        has_error=lasterror.result_code != 1,
        result_code=lasterror.result_code,
        message=lasterror.message,
        result=list(deals)
    )


@mt5_initialize_decor
def get_orders_history() -> Mt5Result[list[mt5.TradeOrder]]:
    from_date = dt.datetime(2020, 1, 1)
    to_date = dt.datetime(2030, 1, 1)

    orders = mt5.history_orders_get(from_date, to_date)

    lasterror = mt5_last_error()

    return Mt5Result(
        has_error=lasterror.result_code != 1,
        result_code=lasterror.result_code,
        message=lasterror.message,
        result=list(orders)
    )
