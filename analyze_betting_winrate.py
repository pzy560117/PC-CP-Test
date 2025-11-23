"""
计算倍投策略下的真实胜率
"""
import json

def analyze_betting_winrate():
    """计算倍投周期的胜率"""
    
    # 读取数据
    data_file = r"d:\PC-Test\data\results\comparison_history.jsonl"
    records = []
    
    with open(data_file, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))
    
    print(f"总记录数: {len(records)}")
    print("=" * 80)
    
    # 分析倍投周期
    # 一个倍投周期 = 从第一次下注到命中(或达到最大倍投次数)
    betting_cycles = []  # 倍投周期列表
    current_cycle = {
        'bets': [],  # 每次下注金额
        'total_bet': 0,  # 总投注
        'result': None,  # 'win' 或 'loss'
        'start_period': None,
        'end_period': None
    }
    
    consecutive_miss = 0
    
    for record in records:
        is_hit = record.get('hit_count', 0) > 0
        period = record.get('period', '')
        
        if current_cycle['start_period'] is None:
            current_cycle['start_period'] = period
        
        # 确定本次下注金额
        if consecutive_miss == 0:
            bet_amount = 1
        elif consecutive_miss == 1:
            bet_amount = 3
        else:
            bet_amount = 9
        
        current_cycle['bets'].append(bet_amount)
        current_cycle['total_bet'] += bet_amount
        
        if is_hit:
            # 命中,周期结束
            current_cycle['end_period'] = period
            win_amount = bet_amount * 2
            profit = win_amount - current_cycle['total_bet']
            
            if profit > 0:
                current_cycle['result'] = 'win'
                current_cycle['profit'] = profit
            elif profit == 0:
                current_cycle['result'] = 'break_even'
                current_cycle['profit'] = 0
            else:
                current_cycle['result'] = 'loss'
                current_cycle['profit'] = profit
            
            current_cycle['consecutive_miss'] = consecutive_miss
            current_cycle['win_amount'] = win_amount
            
            betting_cycles.append(current_cycle)
            
            # 开始新周期
            current_cycle = {
                'bets': [],
                'total_bet': 0,
                'result': None,
                'start_period': None,
                'end_period': None
            }
            consecutive_miss = 0
        else:
            # 未命中,继续倍投
            consecutive_miss += 1
    
    # 如果最后还有未完成的周期(连续未命中到最后)
    if current_cycle['bets']:
        current_cycle['result'] = 'incomplete'
        current_cycle['end_period'] = records[-1].get('period', '')
        current_cycle['profit'] = -current_cycle['total_bet']
        current_cycle['consecutive_miss'] = consecutive_miss
        betting_cycles.append(current_cycle)
    
    # 统计结果
    win_cycles = [c for c in betting_cycles if c['result'] == 'win']
    loss_cycles = [c for c in betting_cycles if c['result'] == 'loss']
    break_even_cycles = [c for c in betting_cycles if c['result'] == 'break_even']
    incomplete_cycles = [c for c in betting_cycles if c['result'] == 'incomplete']
    
    total_completed_cycles = len(win_cycles) + len(loss_cycles) + len(break_even_cycles)
    
    if total_completed_cycles > 0:
        win_rate = (len(win_cycles) / total_completed_cycles) * 100
    else:
        win_rate = 0
    
    print(f"\n【倍投周期分析】")
    print(f"总倍投周期数: {len(betting_cycles)}")
    print(f"完成的周期数: {total_completed_cycles}")
    print(f"  - 盈利周期: {len(win_cycles)}次")
    print(f"  - 亏损周期: {len(loss_cycles)}次")
    print(f"  - 持平周期: {len(break_even_cycles)}次")
    print(f"未完成周期: {len(incomplete_cycles)}次 (数据末尾仍在连续未中)")
    
    print(f"\n【倍投策略胜率】")
    print(f"胜率 = 盈利周期 / 完成周期")
    print(f"胜率 = {len(win_cycles)} / {total_completed_cycles} = {win_rate:.2f}%")
    
    # 分析盈利和亏损周期的详情
    print(f"\n【盈利周期详情】")
    for i, cycle in enumerate(win_cycles[:10], 1):
        print(f"{i}. 期号: {cycle['start_period']}~{cycle['end_period']}, "
              f"连续未中: {cycle['consecutive_miss']}次, "
              f"投注: {cycle['total_bet']}元, "
              f"收益: {cycle['win_amount']}元, "
              f"净利: {cycle['profit']}元")
    
    if len(win_cycles) > 10:
        print(f"... (还有{len(win_cycles)-10}个盈利周期)")
    
    if loss_cycles:
        print(f"\n【亏损周期详情】")
        for i, cycle in enumerate(loss_cycles, 1):
            print(f"{i}. 期号: {cycle['start_period']}~{cycle['end_period']}, "
                  f"连续未中: {cycle['consecutive_miss']}次, "
                  f"投注: {cycle['total_bet']}元, "
                  f"收益: {cycle.get('win_amount', 0)}元, "
                  f"净亏: {cycle['profit']}元")
    
    # 统计不同连续未中次数的盈利情况
    print(f"\n【按连续未中次数统计盈亏】")
    miss_profit_stats = {}
    for cycle in betting_cycles:
        if cycle['result'] != 'incomplete':
            miss_count = cycle['consecutive_miss']
            if miss_count not in miss_profit_stats:
                miss_profit_stats[miss_count] = {
                    'count': 0,
                    'total_profit': 0,
                    'win_count': 0
                }
            
            miss_profit_stats[miss_count]['count'] += 1
            miss_profit_stats[miss_count]['total_profit'] += cycle['profit']
            if cycle['result'] == 'win':
                miss_profit_stats[miss_count]['win_count'] += 1
    
    for miss_count in sorted(miss_profit_stats.keys()):
        stats = miss_profit_stats[miss_count]
        avg_profit = stats['total_profit'] / stats['count']
        win_rate_by_miss = (stats['win_count'] / stats['count']) * 100
        print(f"连续未中{miss_count}次: 出现{stats['count']}次, "
              f"平均盈利: {avg_profit:.2f}元, "
              f"该类胜率: {win_rate_by_miss:.2f}%")
    
    # 总盈亏
    total_profit = sum(c['profit'] for c in betting_cycles)
    total_bet_all = sum(c['total_bet'] for c in betting_cycles)
    
    print(f"\n【总体结果】")
    print(f"总投注: {total_bet_all}元")
    print(f"总盈亏: {total_profit}元")
    if total_bet_all > 0:
        print(f"投资回报率: {(total_profit/total_bet_all)*100:.2f}%")
    
    return {
        'win_rate': win_rate,
        'total_cycles': len(betting_cycles),
        'win_cycles': len(win_cycles),
        'loss_cycles': len(loss_cycles)
    }

if __name__ == "__main__":
    result = analyze_betting_winrate()
