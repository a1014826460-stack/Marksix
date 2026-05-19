import csv
import sys
import os

def remove_empty_rows(input_path, output_path=None):
    """
    删除 CSV 文件中所有完全空白的行（包括仅含空白字符的行）。
    :param input_path:  输入 CSV 文件路径
    :param output_path: 输出 CSV 文件路径，如果为 None 则覆盖原文件
    """
    # 先读取所有非空行
    non_empty_rows = []
    with open(input_path, 'r', encoding='utf-8', newline='') as f:
        reader = csv.reader(f)
        for row in reader:
            # 检查当前行是否所有字段去除空白后都为空（即整行空白）
            if any(cell.strip() for cell in row):
                non_empty_rows.append(row)

    # 确定输出路径
    if output_path is None:
        output_path = input_path

    # 写入过滤后的数据
    with open(output_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerows(non_empty_rows)

    print(f"处理完成。已删除空白行，结果保存至：{output_path}")

if __name__ == '__main__':
    # 使用方法：python remove_empty_rows.py 输入文件.csv [输出文件.csv]
    if len(sys.argv) < 2:
        print("用法: python remove_empty_rows.py <输入文件.csv> [输出文件.csv]")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None

    if not os.path.exists(input_file):
        print(f"错误：文件 '{input_file}' 不存在。")
        sys.exit(1)

    remove_empty_rows(input_file, output_file)