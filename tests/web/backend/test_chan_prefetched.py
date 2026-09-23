from unittest.mock import patch

import pytest

from Chan import CChan
from ChanConfig import CChanConfig
from Common.CEnum import DATA_FIELD, KL_TYPE
from Common.CTime import CTime
from KLine.KLine_Unit import CKLine_Unit


def bar(day, price):
    return CKLine_Unit({DATA_FIELD.FIELD_TIME: CTime(2026, 9, day, 0, 0, auto=False),
        DATA_FIELD.FIELD_OPEN: price, DATA_FIELD.FIELD_HIGH: price + 1,
        DATA_FIELD.FIELD_LOW: price - 1, DATA_FIELD.FIELD_CLOSE: price + .5,
        DATA_FIELD.FIELD_VOLUME: 100})


def test_deferred_load_uses_prefetched_bars_without_provider():
    with patch.object(CChan, 'GetStockAPI', side_effect=AssertionError('provider accessed')):
        chan = CChan('sh.000001', lv_list=[KL_TYPE.K_DAY], config=CChanConfig(), defer_load=True)
        chan.trigger_load({KL_TYPE.K_DAY: [bar(i, 10 + i % 4) for i in range(1, 17)]})
    kl = chan[KL_TYPE.K_DAY]
    assert len(list(kl.klu_iter())) == 16
    assert kl.bi_list is not None
    assert kl.seg_list is not None
    assert kl.zs_list is not None


def test_default_constructor_still_loads():
    with patch.object(CChan, 'load', return_value=iter([None])) as load:
        CChan('sh.000001', lv_list=[KL_TYPE.K_DAY], config=CChanConfig())
    load.assert_called_once()
