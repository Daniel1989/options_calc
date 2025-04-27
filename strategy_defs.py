# strategy_defs.py (or place this dictionary near the top of app.py)

STRATEGY_DETAILS = {
    "Bull Call Spread": {
        "name_cn": "牛市看涨价差",
        "description": "买入一份较低行权价的看涨期权，同时卖出一份相同数量、相同到期日但较高行权价的看涨期权。这是一种限定了最大盈利和最大亏损的策略。",
        "example": "买入1份 6月 100 Call，卖出1份 6月 110 Call。",
        "scenarios": "温和看涨后市，认为标的资产价格会上涨，但涨幅有限（不会超过卖出期权的行权价），同时希望控制成本和风险。"
    },
    "Bear Call Spread": {
        "name_cn": "熊市看涨价差",
        "description": "卖出一份较低行权价的看涨期权，同时买入一份相同数量、相同到期日但较高行权价的看涨期权。通常为收取权利金（Credit Spread），限定了最大盈利和最大亏损。",
        "example": "卖出1份 6月 100 Call，买入1份 6月 110 Call。",
        "scenarios": "温和看跌或中性预期，认为标的资产价格不会上涨（或小幅下跌），尤其是不认为会涨过卖出期权的行权价。主要目的是赚取时间价值和波动率下降带来的收益。"
    },
     "Bear Put Spread": {
        "name_cn": "熊市看跌价差",
        "description": "买入一份较高行权价的看跌期权，同时卖出一份相同数量、相同到期日但较低行权价的看跌期权。限定了最大盈利和最大亏损。",
        "example": "买入1份 6月 105 Put，卖出1份 6月 95 Put。",
        "scenarios": "温和看跌后市，认为标的资产价格会下跌，但跌幅有限（不会低于卖出期权的行权价），同时希望控制成本和风险。"
    },
    "Bull Put Spread": {
        "name_cn": "牛市看跌价差",
        "description": "卖出一份较高行权价的看跌期权，同时买入一份相同数量、相同到期日但较低行权价的看跌期权。通常为收取权利金（Credit Spread），限定了最大盈利和最大亏损。",
        "example": "卖出1份 6月 105 Put，买入1份 6月 95 Put。",
        "scenarios": "温和看涨或中性预期，认为标的资产价格不会下跌（或小幅上涨），尤其是不认为会跌破卖出期权的行权价。主要目的是赚取时间价值和波动率下降带来的收益。"
    },
    "Long Straddle": {
        "name_cn": "买入跨式",
        "description": "同时买入相同数量、相同到期日、相同行权价的看涨期权和看跌期权。",
        "example": "买入1份 6月 100 Call，买入1份 6月 100 Put。",
        "scenarios": "预期标的资产价格将发生大幅波动，但不确定方向。通常在重大事件（如财报、选举）前使用，预期波动率会上升。"
    },
    "Short Straddle": {
        "name_cn": "卖出跨式",
        "description": "同时卖出相同数量、相同到期日、相同行权价的看涨期权和看跌期权。",
        "example": "卖出1份 6月 100 Call，卖出1份 6月 100 Put。",
        "scenarios": "预期标的资产价格将在行权价附近窄幅波动，波动率将下降或保持稳定。目的是赚取期权的时间价值。风险敞口巨大。"
    },
     "Long Strangle": {
        "name_cn": "买入宽跨式",
        "description": "同时买入相同数量、相同到期日的价外(OTM)看涨期权和价外(OTM)看跌期权（行权价不同）。",
        "example": "买入1份 6月 105 Call，买入1份 6月 95 Put。",
        "scenarios": "预期标的资产价格将发生大幅波动，但不确定方向，且相比跨式策略成本更低，但需要价格波动幅度更大才能盈利。"
    },
    "Short Strangle": {
        "name_cn": "卖出宽跨式",
        "description": "同时卖出相同数量、相同到期日的价外(OTM)看涨期权和价外(OTM)看跌期权（行权价不同）。",
        "example": "卖出1份 6月 105 Call，卖出1份 6月 95 Put。",
        "scenarios": "预期标的资产价格将在两个行权价之间窄幅波动，波动率将下降或保持稳定。目的是赚取时间价值，风险敞口巨大。"
    },
     "Covered Call": {
        "name_cn": "备兑看涨（抛补式）",
        "description": "持有标的资产（通常为100股的整数倍），同时卖出相应数量的看涨期权。",
        "example": "持有100股XYZ股票，卖出1份 6月 105 Call。",
        "scenarios": "对持有的股票前景中性或温和看好，希望通过卖出看涨期权增加额外收入（权利金），愿意放弃股票价格大幅上涨的部分潜在收益。"
    },
     "Protective Put": {
        "name_cn": "保护性看跌",
        "description": "持有标的资产（通常为100股的整数倍），同时买入相应数量的看跌期权。",
        "example": "持有100股XYZ股票，买入1份 6月 95 Put。",
        "scenarios": "长期看好持有的股票，但担心短期内可能出现回调或下跌，希望通过买入看跌期权来对冲下行风险（相当于购买保险）。"
    },
     "Long Call Butterfly": {
        "name_cn": "买入蝶式看涨",
        "description": "买入1份低行权价Call，卖出2份中间行权价Call，买入1份高行权价Call。三者行权价等距，到期日相同。",
        "example": "买入1份 6月 90 Call, 卖出2份 6月 100 Call, 买入1份 6月 110 Call。",
        "scenarios": "预期标的资产价格在到期日时会非常接近中间行权价，且波动率较低。最大利润在中间行权价实现，风险有限。"
    },
    "Iron Condor": {
        "name_cn": "铁鹰式价差",
        "description": "由一个牛市看跌价差(Bull Put Spread)和一个熊市看涨价差(Bear Call Spread)组成，所有期权均为价外(OTM)，到期日相同。是一种限定风险和收益的策略。",
        "example": "买入1份 6月 90 Put, 卖出1份 6月 95 Put, 卖出1份 6月 105 Call, 买入1份 6月 110 Call。",
        "scenarios": "预期标的资产价格在到期日时将在中间两个（卖出的）行权价之间窄幅波动，且隐含波动率会下降或保持稳定。目的是赚取时间价值。"
    },
    # --- Fallback / Default entries ---
    "Custom Strategy": {
        "name_cn": "自定义策略",
        "description": "由多个期权或/和标的资产头寸组成的非标准策略。",
        "example": "N/A",
        "scenarios": "根据特定的市场预期或风险管理需求定制。"
    },
    "Custom Option Spread": {
        "name_cn": "自定义期权组合",
        "description": "由多个期权头寸组成的非标准策略。",
        "example": "N/A",
        "scenarios": "根据特定的市场预期或风险管理需求定制。"
    },
     "Mixed Underlying/Option Strategy": {
        "name_cn": "混合策略",
        "description": "同时包含标的资产头寸和期权头寸的非标准策略。",
        "example": "N/A",
        "scenarios": "根据特定的市场预期或风险管理需求定制。"
    },
    "Long Underlying": {
        "name_cn": "标的多头",
        "description": "直接持有标的资产。",
        "example": "买入100股XYZ",
        "scenarios": "看好标的资产未来价格会上涨。"
     },
     "Short Underlying": {
        "name_cn": "标的空头",
        "description": "融券卖出标的资产。",
        "example": "卖空100股XYZ",
        "scenarios": "看空标的资产未来价格会下跌。"
     },
     "Long Call": {
        "name_cn": "买入看涨期权",
        "description": "支付权利金，获得在未来以特定价格买入标的资产的权利。",
        "example": "买入1份 6月 100 Call",
        "scenarios": "强烈看涨标的资产，认为价格会大幅上涨超过行权价+权利金成本，或预期波动率上升。利用杠杆效应。"
     },
      "Short Call": {
        "name_cn": "卖出看涨期权 (Naked)",
        "description": "收取权利金，承担在未来以特定价格卖出标的资产的义务（若无备兑）。风险无限。",
        "example": "卖出1份 6月 110 Call (无对应股票)",
        "scenarios": "看跌或中性预期，认为标的资产价格不会上涨到行权价之上。赚取时间价值和波动率下降收益。"
     },
      "Long Put": {
        "name_cn": "买入看跌期权",
        "description": "支付权利金，获得在未来以特定价格卖出标的资产的权利。",
        "example": "买入1份 6月 95 Put",
        "scenarios": "强烈看跌标的资产，认为价格会大幅下跌低于行权价-权利金成本，或预期波动率上升。利用杠杆效应或对冲多头头寸。"
     },
      "Short Put": {
        "name_cn": "卖出看跌期权 (Naked)",
        "description": "收取权利金，承担在未来以特定价格买入标的资产的义务。",
        "example": "卖出1份 6月 90 Put",
        "scenarios": "看涨或中性预期，认为标的资产价格不会下跌到行权价之下，或愿意以行权价买入标的。赚取时间价值和波动率下降收益。"
     },
    "Unknown Strategy": {
        "name_cn": "未知策略",
        "description": "无法识别的头寸组合。",
        "example": "N/A",
        "scenarios": "N/A"
    },
    "Empty Strategy": {
        "name_cn": "空策略",
        "description": "策略中不包含任何头寸。",
        "example": "N/A",
        "scenarios": "N/A"
    }
    # Add more strategies here as identified...
}

STRATEGY_SCENARIO_MAP = {
    "Long Call": ["big_rally"],
    "Bull Call Spread": ["big_rally", "small_rally"],
    "Bull Put Spread": ["small_rally", "range_bound"], # Often used for neutral-to-bullish
    "Long Underlying": ["big_rally", "small_rally"],

    "Long Put": ["big_drop"],
    "Bear Put Spread": ["big_drop", "small_drop"],
    "Bear Call Spread": ["small_drop", "range_bound"], # Often used for neutral-to-bearish

    "Protective Put": ["big_drop", "small_drop"], # Primarily downside protection
    "Covered Call": ["small_rally", "range_bound"], # Benefits from stable or slight rise

    "Long Straddle": ["big_rally", "big_drop"], # Volatility plays
    "Long Strangle": ["big_rally", "big_drop"], # Volatility plays

    "Short Straddle": ["range_bound"], # Time decay / Low vol
    "Short Strangle": ["range_bound"], # Time decay / Low vol
    "Iron Condor": ["range_bound"], # Time decay / Low vol
    "Iron Butterfly": ["range_bound"], # (If you add this type) Time decay / Low vol
    "Long Call Butterfly": ["range_bound"], # Pin risk / Low vol around middle strike
    "Long Put Butterfly": ["range_bound"], # (If you add this type) Pin risk / Low vol around middle strike

    "Short Call": ["big_drop", "small_drop", "range_bound"], # Benefits if price doesn't rise significantly
    "Short Put": ["big_rally", "small_rally", "range_bound"], # Benefits if price doesn't fall significantly

    # Fallbacks can be classified broadly or left unclassified
    "Mixed Underlying/Option Strategy": ["unclassified"],
    "Custom Option Spread": ["unclassified"],
    "Custom Underlying Strategy": ["unclassified"],
    "LLM Identified": ["unclassified"], # Can't reliably classify LLM output without further parsing
    "Unknown Strategy": ["unclassified"],
    "Empty Strategy": [], # Doesn't fit anywhere
    # Add default/error types from LLM if needed
    "LLM Disabled": ["unclassified"],
    "LLM Parse Error": ["unclassified"],
    "LLM API Error": ["unclassified"],
    "LLM Unknown Error": ["unclassified"],
}