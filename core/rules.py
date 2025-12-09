import re
import pandas as pd

class PricingRuleEngine:
    def __init__(self):
        self.base_price_rules = {} 
        self.adjustment_rules = []

    def parse_rules(self, text):
        """
        解析自然语言规则文本
        """
        if not text:
            return

        # 1. 预处理：统一标点符号，分割成单条规则
        # 将中文标点替换为英文分号，作为规则分隔符
        text = text.replace("，", ";").replace(",", ";").replace("；", ";").replace("。", ";").replace(":", ";").replace("：", ";")
        segments = [s.strip() for s in text.split(";") if s.strip()]

        for seg in segments:
            self._parse_segment(seg)

    def _parse_segment(self, text):
        """
        解析单条规则片段
        """
        # 1. 识别基价定义规则 (e.g., "以16A槽为基价")
        if "为基价" in text:
            match = re.search(r"以?([A-Z0-9]+)[槽角工]?", text)
            if match:
                model = match.group(1)
                # 简单的推断品名（如果文本包含槽/角/工）
                product = None
                if "槽" in text: product = "槽钢"
                elif "角" in text: product = "角钢"
                elif "工" in text: product = "工字钢"
                
                if product:
                    self.base_price_rules[product] = model
            return

        # 2. 识别加价规则
        # 提取加价金额
        price_match = re.search(r"加价(\d+)元?", text)
        if not price_match:
            return # 不是加价规则
        
        adjustment = float(price_match.group(1))
        
        rule = {
            "adjustment": adjustment,
            "conditions": {}
        }

        # --- 解析条件 ---

        # A. 长度条件 (e.g., "9米12米", "6m")
        lengths = re.findall(r"(\d+)(?:米|m)", text)
        if lengths:
            rule["conditions"]["length"] = [float(l) for l in lengths]

        # B. 重量/公斤条件 (e.g., "4-5公斤", "13.5-14.5公斤")
        weight_range = re.search(r"(\d+(?:\.\d+)?)-(\d+(?:\.\d+)?)(?:公斤|kg)", text)
        if weight_range:
            rule["conditions"]["weight_min"] = float(weight_range.group(1))
            rule["conditions"]["weight_max"] = float(weight_range.group(2))

        # C. 负差条件 (e.g., "18-20负差")
        diff_range = re.search(r"(\d+(?:\.\d+)?)-(\d+(?:\.\d+)?)(?:负差)", text)
        if diff_range:
            rule["conditions"]["diff_min"] = float(diff_range.group(1))
            rule["conditions"]["diff_max"] = float(diff_range.group(2))

        # D. 型号条件
        # 复杂点：可能是范围 "22AB-30AB"，可能是单个 "32C"，可能是特定规格 "40*40*5*6m"
        
        # D1. 特定全规格匹配 (e.g. 40*40*5*6m)
        spec_match = re.search(r"(\d+\*[\d\*m]+)", text)
        if spec_match and "*" in spec_match.group(1):
             # 这是一个具体的规格字符串，可能包含长宽厚长
             # 简单处理：如果规则里写了具体规格，我们假设它匹配的是“型号”或者“品名+型号”的组合
             # 这里暂存为 keyword 匹配
             rule["conditions"]["spec_keyword"] = spec_match.group(1)
        else:
            # D2. 型号范围 (e.g. 22AB-30AB)
            # 提取所有类似型号的字符串
            # 假设型号由 数字+字母 组成
            # 先把 "9米", "12米", "4-5公斤" 等已解析的部分去掉，避免干扰？
            # 或者直接正则匹配 "XX-XX"
            
            # 尝试匹配范围
            range_match = re.search(r"([0-9]+[A-Z]*)-([0-9]+[A-Z]*)(?:槽|角|工)?", text)
            if range_match:
                start_model = range_match.group(1)
                end_model = range_match.group(2)
                # 提取数字部分进行比较
                rule["conditions"]["model_range"] = (self._extract_model_num(start_model), self._extract_model_num(end_model))
                # 提取后缀字母限制 (e.g. 22AB - 30AB implies AB series)
                suffix = "".join([c for c in start_model if not c.isdigit()])
                if suffix:
                    rule["conditions"]["model_suffix"] = suffix
            else:
                # D3. 单个型号或列表 (e.g. 32AB, 32C)
                # 排除掉前面已经匹配到的长度、重量数字
                # 这是一个难点，简单策略：匹配 "数字+字母" 或 "纯数字(大)"
                # 这里的逻辑比较脆弱，针对特定例子优化
                
                # 找 "32AB" 这种
                models = re.findall(r"\b(\d+[A-Z]+)\b", text)
                if models:
                    rule["conditions"]["models"] = models
                else:
                    # 找 "30角" -> 30
                    simple_model = re.search(r"(\d+)(?:槽|角|工)", text)
                    if simple_model:
                         rule["conditions"]["models"] = [simple_model.group(1)]

        # E. 关键字匹配 (新增)
        # 如果没有匹配到复杂的型号范围或特定型号，尝试提取剩余文本作为关键字
        # 简单的“减法”逻辑：去掉已识别的加价、长度、重量、负差等，剩下的就是关键字
        
        # 构造一个用于清理的字符串
        clean_text = text
        # 去掉加价部分
        clean_text = clean_text.replace(price_match.group(0), "")
        # 去掉长度
        for l in lengths:
            clean_text = clean_text.replace(f"{l}米", "").replace(f"{l}m", "")
        # 去掉重量
        if weight_range:
            clean_text = clean_text.replace(weight_range.group(0), "")
        # 去掉负差
        if diff_range:
            clean_text = clean_text.replace(diff_range.group(0), "")
        # 去掉型号范围
        if 'range_match' in locals() and range_match:
            clean_text = clean_text.replace(range_match.group(0), "")
        
        # 清理剩余的标点和空格
        keyword = clean_text.strip()
        # 如果剩下的文本包含汉字或字母，且长度>0，视为关键字
        if keyword and (re.search(r'[\u4e00-\u9fa5]', keyword) or re.search(r'[A-Za-z]', keyword)):
             # 排除一些无意义词汇
             if keyword not in ["统一", "全部", "所有"]:
                 rule["conditions"]["keyword"] = keyword

        # F. 品名推断 (保留但非强制，作为辅助)
        # 如果关键字里已经包含了品名信息（如“简装管”），这里就不需要额外限制了
        # 只有当没有关键字时，才使用这些硬编码的品名限制
        if "keyword" not in rule["conditions"]:
            if "槽" in text: rule["conditions"]["product"] = "槽钢"
            elif "角" in text: rule["conditions"]["product"] = "角钢"
            elif "工" in text: rule["conditions"]["product"] = "工字钢"

        self.adjustment_rules.append(rule)

    def _extract_model_num(self, model_str):
        match = re.search(r"(\d+)", model_str)
        return int(match.group(1)) if match else 0

    def get_base_model(self, product_name):
        for key, val in self.base_price_rules.items():
            if key in product_name:
                return val
        return None

    def calculate_adjustment(self, row_data):
        """
        根据行数据计算加价
        row_data: dict, 包含 'product', 'model', 'length', 'weight', 'diff' 等
        """
        total_adj = 0
        
        product = str(row_data.get("product", ""))
        model = str(row_data.get("model", ""))
        length = row_data.get("length", 0)
        weight = row_data.get("weight", 0)
        diff = row_data.get("diff", 0) # 负差
        
        model_num = self._extract_model_num(model)

        for rule in self.adjustment_rules:
            cond = rule["conditions"]
            match = True

            # 1. 品名匹配
            if "product" in cond and cond["product"] not in product:
                match = False

            # 2. 长度匹配
            if match and "length" in cond:
                # 模糊匹配：如果规则是9米，数据是9.0或9
                if not any(abs(l - length) < 0.1 for l in cond["length"]):
                    match = False

            # 3. 重量范围
            if match and "weight_min" in cond:
                if not (cond["weight_min"] <= weight <= cond["weight_max"]):
                    match = False

            # 4. 负差范围
            if match and "diff_min" in cond:
                if not (cond["diff_min"] <= diff <= cond["diff_max"]):
                    match = False

            # 5. 型号范围
            if match and "model_range" in cond:
                min_m, max_m = cond["model_range"]
                if not (min_m <= model_num <= max_m):
                    match = False
                # 检查后缀 (e.g. AB)
                if "model_suffix" in cond:
                    if cond["model_suffix"] not in model:
                        match = False

            # 6. 特定型号列表
            if match and "models" in cond:
                # 检查当前型号是否包含在列表中 (e.g. "32AB" in ["32AB"])
                # 或者数字匹配 "30" in ["30"]
                is_in = False
                for m in cond["models"]:
                    if m == model or (m.isdigit() and int(m) == model_num):
                        is_in = True
                        break
                if not is_in:
                    match = False
            
            # 7. 规格关键字 (e.g. 40*40*5*6m)
            if match and "spec_keyword" in cond:
                # 这是一个很强的匹配，通常需要拼接原始字符串来检查
                # 假设 row_data 有 'raw_spec'
                raw_spec = str(row_data.get("raw_spec", ""))
                # 简单的归一化比较
                k = cond["spec_keyword"].replace("m", "").replace("*", "")
                t = raw_spec.replace("m", "").replace("*", "").replace(" ", "")
                if k not in t:
                    match = False

            # 8. 通用关键字匹配 (新增)
            if match and "keyword" in cond:
                kw = cond["keyword"]
                # 检查品名或型号中是否包含关键字
                # 也可以检查 raw_spec
                if kw not in product and kw not in model and kw not in str(row_data.get("raw_spec", "")):
                    match = False

            if match:
                total_adj += rule["adjustment"]

        return total_adj
