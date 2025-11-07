import asyncio
from typing import Iterator
import numpy as np
from more_itertools import last
from numpy._typing import NDArray
from py_candlestick import Symbol, TimeFrame, Chart
from src.mt5_source import mt5_initialize_decor
import MetaTrader5._core as mt5


@mt5_initialize_decor
async def stream_market_data(
        symbol: Symbol,
        timeframe: TimeFrame,
        as_chart: bool = False,
        history_count: int = 100,
) -> Iterator[Chart] | Iterator[NDArray[tuple]] | None:
    data = mt5.copy_rates_from_pos(
        symbol.symbol_fullname,
        timeframe.mt5_value,
        1,
        history_count,
    )

    yield Chart.from_mt5_data(data, timeframe) if as_chart else data

    while True:

        await asyncio.sleep(5)

        last_row = last(data)
        last_time = last_row[0]

        data = mt5.copy_rates_from_pos(
            symbol.symbol_fullname,
            timeframe.mt5_value,
            1,
            5,
        )

        new_data = np.array([i for i in data if i[0] > last_time])

        if new_data.size == 0:
            continue

        yield Chart.from_mt5_data(new_data, timeframe) if as_chart else data


@mt5_initialize_decor
async def stream_multiple_market_data(
        symbols: list[Symbol],
        timeframe: TimeFrame,
        as_chart: bool = False,
        history_count: int = 100,
) -> Iterator[Chart] | None:
    data_dict = {symbol: None for symbol in symbols}

    for symbol in symbols:
        data = mt5.copy_rates_from_pos(
            symbol.symbol_fullname,
            timeframe.mt5_value,
            1,
            history_count,
        )
        data_dict[symbol] = data

        yield Chart.from_mt5_data(data_dict[symbol], symbol, timeframe)

    while True:

        await asyncio.sleep(5)

        for symbol in symbols:

            data = data_dict[symbol]

            last_row = last(data)
            last_time = last_row[0]

            data = mt5.copy_rates_from_pos(
                symbol.symbol_fullname,
                timeframe.mt5_value,
                1,
                5,
            )

            new_data = np.array([i for i in data if i[0] > last_time])

            if new_data.size == 0:
                continue

            yield Chart.from_mt5_data(new_data, timeframe) if as_chart else data
