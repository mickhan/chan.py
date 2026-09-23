from Common.CEnum import AUTYPE, KL_TYPE

PERIOD_TO_KL_TYPE = {
    "5m": KL_TYPE.K_5M,
    "15m": KL_TYPE.K_15M,
    "30m": KL_TYPE.K_30M,
    "60m": KL_TYPE.K_60M,
    "1d": KL_TYPE.K_DAY,
    "1w": KL_TYPE.K_WEEK,
    "1mo": KL_TYPE.K_MON,
}
ADJUSTMENT_TO_AUTYPE = {
    "none": AUTYPE.NONE,
    "qfq": AUTYPE.QFQ,
    "hfq": AUTYPE.HFQ,
}
