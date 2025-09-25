import BuffApiPublic
import argparse
import json

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--checklist_file', type=str, required=True, help='Input file path')
    parser.add_argument('--output_file', type=str, default='check_results.json', help='Output file path')
    parser.add_argument('--cookie', type=str, required=True, help='Buff cookie for authentication')

    args = parser.parse_args()
    return args

def main(args):
    checklist_file = args.checklist_file
    checklist = []
    # checklist_file is json
    with open(checklist_file, 'r', encoding='utf-8') as f:
        checklist = json.load(f)

    Buff = BuffApiPublic.BuffAccount(args.cookie)
    check_result_json_list = []    
    for item in checklist:
        check_result_json_list.append(Buff.get_sell_order(item['goods_id'], page_num=1, game_name=item['game'], sort_by='default', proxy=None))
    
    output_file = args.output_file
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(check_result_json_list, f, ensure_ascii=False, indent=4)

    print(f"Check completed. Results saved to {output_file}")

if __name__ == '__main__':
    args = parse_args()

    main(args)
        
