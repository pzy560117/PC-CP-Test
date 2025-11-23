"""
分析数据库中的命中情况和倍投策略
"""
import json

def analyze_betting_strategy():
    """分析命中情况和倍投策略"""
    
    # 读取数据
    data_file = r"d:\PC-Test\data\results\comparison_history.jsonl"
    records = []
    
    with open(data_file, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))
    
    print(f"总记录数: {len(records)}")
    print("=" * 80)
    
    # 分析连续未命中情况
    max_consecutive_miss = 0  # 最大连续未命中次数
    current_consecutive_miss = 0  # 当前连续未命中次数
    consecutive_miss_list = []  # 所有连续未命中的记录
    
    for record in records:
        is_hit = record.get('hit_count', 0) > 0
        
        if not is_hit:
            current_consecutive_miss += 1
        else:
            if current_consecutive_miss > 0:
                consecutive_miss_list.append(current_consecutive_miss)
                if current_consecutive_miss > max_consecutive_miss:
                    max_consecutive_miss = current_consecutive_miss
            current_consecutive_miss = 0
    
    # 最后可能还有未命中的
    if current_consecutive_miss > 0:
        consecutive_miss_list.append(current_consecutive_miss)
        if current_consecutive_miss > max_consecutive_miss:
            max_consecutive_miss = current_consecutive_miss
    
    print(f"\n【连续未命中分析】")
    print(f"最大连续未命中次数: {max_consecutive_miss}")
    print(f"连续未命中段数: {len(consecutive_miss_list)}")
    print(f"所有连续未命中情况: {consecutive_miss_list}")
    
    # 统计各种连续未命中次数出现的频率
    miss_count_freq = {}
    for count in consecutive_miss_list:
        miss_count_freq[count] = miss_count_freq.get(count, 0) + 1
    
    print(f"\n【连续未命中次数统计】")
    for count in sorted(miss_count_freq.keys()):
        print(f"连续未中{count}次: {miss_count_freq[count]}次")
    
    # 按照倍投策略计算
    # 1期下1,没中2期下3,没中3期下9
    print(f"\n{'='*80}")
    print(f"【倍投策略分析】")
    print(f"策略: 1期下1,没中2期下3,没中3期下9")
    print(f"说明: 第1次下注1元,第2次下注3元,第3次及以后下注9元")
    print(f"{'='*80}")
    
    total_bet = 0  # 总投注
    total_win = 0  # 总收益(假设命中返还2倍)
    current_miss = 0  # 当前连续未命中
    betting_history = []
    
    for i, record in enumerate(records, 1):
        is_hit = record.get('hit_count', 0) > 0
        period = record.get('period', '')
        
        # 确定本次下注金额
        if current_miss == 0:
            bet_amount = 1
        elif current_miss == 1:
            bet_amount = 3
        else:
            bet_amount = 9
        
        total_bet += bet_amount
        
        if is_hit:
            # 命中,假设返还2倍
            win_amount = bet_amount * 2
            total_win += win_amount
            profit = win_amount - bet_amount
            
            betting_history.append({
                'period': period,
                'consecutive_miss': current_miss,
                'bet': bet_amount,
                'result': '中',
                'win': win_amount,
                'profit': profit
            })
            
            current_miss = 0
        else:
            # 未命中
            betting_history.append({
                'period': period,
                'consecutive_miss': current_miss,
                'bet': bet_amount,
                'result': '未中',
                'win': 0,
                'profit': -bet_amount
            })
            
            current_miss += 1
    
    # 计算最终结果
    net_profit = total_win - total_bet
    win_rate = (len([r for r in records if r.get('hit_count', 0) > 0]) / len(records)) * 100
    
    print(f"\n【总体统计】")
    print(f"总投注: {total_bet} 元")
    print(f"总收益: {total_win} 元")
    print(f"净盈亏: {net_profit} 元")
    print(f"投资回报率: {(net_profit/total_bet)*100:.2f}%")
    print(f"命中率: {win_rate:.2f}%")
    
    # 显示一些关键的投注记录
    print(f"\n【关键投注记录(连续未中>=2次后命中的情况)】")
    key_records = [r for r in betting_history if r['consecutive_miss'] >= 2 and r['result'] == '中']
    
    if key_records:
        for record in key_records[:10]:  # 只显示前10条
            print(f"期号: {record['period']}, 连续未中: {record['consecutive_miss']}次, "
                  f"投注: {record['bet']}元, 结果: {record['result']}, "
                  f"收益: {record['win']}元, 盈利: {record['profit']}元")
        
        if len(key_records) > 10:
            print(f"... (还有{len(key_records)-10}条类似记录)")
    
    # 显示最长连续未命中的情况
    print(f"\n【最长连续未命中详情】")
    print(f"最长连续未命中: {max_consecutive_miss}次")
    
    if max_consecutive_miss >= 3:
        print(f"注意: 根据倍投策略,连续未中3次及以上,每次都需要投注9元!")
        print(f"如果连续未中{max_consecutive_miss}次,需要投注: ", end="")
        
        total_for_max = 0
        for i in range(max_consecutive_miss):
            if i == 0:
                bet = 1
            elif i == 1:
                bet = 3
            else:
                bet = 9
            total_for_max += bet
        
        print(f"{total_for_max}元")
    
    return {
        'max_consecutive_miss': max_consecutive_miss,
        'total_bet': total_bet,
        'total_win': total_win,
        'net_profit': net_profit,
        'win_rate': win_rate
    }

if __name__ == "__main__":
    result = analyze_betting_strategy()
