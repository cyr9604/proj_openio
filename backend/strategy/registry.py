STRATEGIES = {
    "ma520": {
        "name": "MA520均线策略",
        "description": "基于5日线(MA5)和20日线(MA20)的经典均线交易系统。以MA20定义中期趋势方向，只做上升趋势；MA5金叉/死叉提供买卖信号。结合成交量、MACD等辅助指标过滤假信号。",
        "buy_rules": [
            {
                "type": "金叉买入",
                "condition": "5日线上穿20日线，且20日线向上（斜率>0.5），成交量≥1.5倍，股价站上20日线",
                "action": "买入30%仓位",
                "priority": 2,
            },
            {
                "type": "回踩买入",
                "condition": "10日内有金叉，股价回踩20日线（偏离0-3%），回调缩量（均量/最大量≤0.7），当日带量站上5日线",
                "action": "买入30%仓位",
                "priority": 3,
            },
            {
                "type": "粘合发散买入",
                "condition": "MA5与MA20粘合（差距<1.5%持续5日以上），放量（量比≥1.5）突破前期高点",
                "action": "买入40%仓位（快进快出）",
                "priority": 4,
            },
            {
                "type": "共振买入",
                "condition": "金叉和MACD由负转正在5日内先后出现，双信号共振确认",
                "action": "买入50%仓位（半仓）",
                "priority": 1,
            },
        ],
        "sell_rules": [
            {
                "type": "常规止盈",
                "condition": "持仓盈利达到10%-20%",
                "action": "止盈卖出，落袋为安",
                "priority": 1,
            },
            {
                "type": "最小止盈",
                "condition": "持仓盈利3%-5%时，收盘价从上方跌破MA20线",
                "action": "卖出止盈，锁定3%-5%利润",
                "priority": 2,
            },
            {
                "type": "死叉卖出",
                "condition": "MA5下穿MA20（死叉），强势趋势结束信号",
                "action": "卖出清仓",
                "priority": 3,
            },
            {
                "type": "跌破5日线止损",
                "condition": "连续3日收盘价跌破5日线，且价格低于买入价",
                "action": "止损卖出",
                "priority": 4,
            },
            {
                "type": "放量破20日线止损",
                "condition": "放量（量比≥1.5）跌破20日线",
                "action": "无条件清仓，最大亏损控制在5%以内",
                "priority": 5,
            },
        ],
        "add_rules": [
            {
                "condition": "已持仓且处于盈利状态，20日线持续向上，当前总仓位不超过50%",
                "action": "加仓20%仓位（最高总仓位5成）",
            },
        ],
    },
}


def get_all_strategies() -> dict[str, dict]:
    return {
        k: {"name": v["name"], "description": v["description"]}
        for k, v in STRATEGIES.items()
    }


def get_strategy_detail(name: str) -> dict | None:
    return STRATEGIES.get(name)
