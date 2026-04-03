# 这是identify_first_buy函数的正确实现

def identify_first_buy(trends, df):
    """识别一买
    
    逻辑：
    下降趋势ABCD，最低点abcd
    
    比较步骤：
    1. B和A比较：如果AB差距<1%（形成中枢），继续用C和A比较
    2. C和A比较：如果AC差距>1%，比较A和C的背驰
    3. 如果AC差距<1%，继续用D和A比较
    
    """
    downs = [t for t in trends if t['type'] == '下降']
    
    for i, t in enumerate(downs):
        if i == 0:
            continue
        
        td = extract_trend_data(t, df)
        ef = t['end_fenxing']
        
        if ef[1] != '底':
            continue
        
        curr_low = ef[2]['low']
        
        pd_t = None
        compare_idx = i - 1
        
        while compare_idx >= 0:
            prev_low = downs[compare_idx]['end_fenxing'][2]['low']
            low_diff_pct = abs(curr_low - prev_low) / prev_low * 100
            
            if low_diff_pct > 1:
                # curr和prev不形成中枢，使用prev进行比较
                pd_t = extract_trend_data(downs[compare_idx], df)
                break
            else:
                # curr和prev形成中枢，继续往前找
                compare_idx -= 1
        
        # 进行背驰检测
        div = detect_divergence(td, pd_t, 'bottom')
        
        if div and div['has_divergence']:
            is_new_low = div['price_new_low']
            yangxian_pct = calculate_yangxian_pct(df, td['end_idx'], ef[2]['low'])
            
            cond_desc = []
            if div['cond_a']:
                cond_desc.append("绿柱面积减少")
            if div['cond_b']:
                cond_desc.append("绿柱高度降低")
            if div['cond_c']:
                cond_desc.append("下跌力度减弱")
            
            results.append(SignalPoint(
                date=str(ef[2]['date'])[:10],
                price=ef[2]['low'],
                signal_type='buy',
                level=1,
                fenxing_index=ef[0],
                trend_index=t['index'],
                kline_index=td['end_idx'],
                macd_info={
                    '是否背驰': '是' if cond_desc else '否',
                    '背驰详情': '，'.join(cond_desc) if cond_desc else '无',
                    '在中枢内': '是' if div['in_zhongshu'] else '否',
                    '价格差%': f"{div['price_diff_pct']:.2f}%",
                    '绿柱面积': f"{td['green_area']:.4f}",
                    '绿柱高度': f"{td['green_bar_height']:.4f}",
                    '力度': f"{td['force']:.4f}",
                },
                is_new_low=is_new_low,
                yangxian_pct=yangxian_pct
            ))
    
    return results
