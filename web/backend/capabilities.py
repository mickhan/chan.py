from Common.CEnum import AUTYPE, KL_TYPE

PERIOD_TO_KL_TYPE = {
    "5m": KL_TYPE.K_5M,
    "30m": KL_TYPE.K_30M,
    "1d": KL_TYPE.K_DAY,
    "1w": KL_TYPE.K_WEEK,
}
ADJUSTMENT_TO_AUTYPE = {
    "none": AUTYPE.NONE,
    "qfq": AUTYPE.QFQ,
    "hfq": AUTYPE.HFQ,
}
