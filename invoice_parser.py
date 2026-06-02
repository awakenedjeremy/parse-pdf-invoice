import pdfplumber
import os
from decimal import Decimal


def _compact(text):
    return text.replace(' ', '').replace('\u3000', '').replace('\xa0', '')


def _extract_amount_from_line(ls):
    tokens = ls.split()
    for token in tokens:
        cleaned = ''.join(c for c in token if c.isdigit() or c == '.')
        cleaned = cleaned.replace(',', '')
        if cleaned:
            try:
                return Decimal(cleaned)
            except Exception:
                continue
    return None


def _has_company_ending(s):
    keywords = ['有限公司', '有限责任公司', '股份有限公司', '股份公司',
                '集团公司', '集团本部', '事务所', '合伙企业', '厂商']
    return any(kw in s for kw in keywords)


def extract_invoice_info(pdf_path):
    try:
        with pdfplumber.open(pdf_path) as pdf:
            text = ""
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text

            lines = text.split('\n')
            invoice_no = None
            seller_name = None
            amount = None

            for i, line in enumerate(lines):
                ls = line.strip()
                if not ls:
                    continue
                compact = _compact(ls)

                if invoice_no is None:
                    for kw in ['发票号码', '发票号', '号码']:
                        if kw in compact:
                            digits = ''.join(c for c in ls if c.isdigit())
                            if digits:
                                invoice_no = digits
                            break

                if seller_name is None:
                    for kw in ['销售方名称', '销货方名称']:
                        if kw in compact:
                            parts = compact.split('名称', 1)
                            if len(parts) > 1:
                                rest = parts[1].strip().lstrip('：: ')
                                if rest:
                                    seller_name = rest
                                elif i + 1 < len(lines):
                                    seller_name = _compact(lines[i + 1].strip())
                            break
                    if seller_name is None:
                        for marker in ['售名称', '销名称', '卖方名称']:
                            if marker in compact:
                                parts = compact.split(marker, 1)
                                if len(parts) > 1:
                                    rest = parts[1].strip().lstrip('：: ')
                                    if rest:
                                        seller_name = rest
                                break
                    if seller_name is None:
                        if '销售方' in compact or '销货方' in compact:
                            for j in range(i + 1, min(i + 4, len(lines))):
                                next_line = _compact(lines[j].strip())
                                if '名称' in next_line:
                                    parts = next_line.split('名称', 1)
                                    if len(parts) > 1:
                                        rest = parts[1].strip().lstrip('：: ')
                                        if rest:
                                            seller_name = rest
                                            break
                                elif '有限公司' in next_line or '有限责任' in next_line:
                                    seller_name = next_line
                                    break
                    if seller_name is None and '名称' in compact:
                        for nm in ['名称：', '名称:']:
                            parts = ls.split(nm)
                            if len(parts) >= 3:
                                rest = parts[-1].strip()
                                if rest and '信用代码' not in rest and '纳税人' not in rest:
                                    seller_name = rest
                                    break

            if seller_name is None:
                for ls in lines:
                    ls = ls.strip()
                    if not ls:
                        continue
                    parts = ls.split()
                    company_names = [p for p in parts if _has_company_ending(p)]
                    if len(company_names) >= 2 and '信用代码' not in ls and '纳税人' not in ls:
                        seller_name = company_names[-1]
                        break

            for i, line in enumerate(lines):
                ls = line.strip()
                if not ls:
                    continue
                compact = _compact(ls)
                if amount is None and '价税合计' in compact:
                    amount = _extract_amount_from_line(ls)

            if amount is None:
                for i, line in enumerate(lines):
                    ls = line.strip()
                    if not ls:
                        continue
                    compact = _compact(ls)
                    if amount is None and '合计' in compact:
                        amount = _extract_amount_from_line(ls)

            if amount is None:
                for i, line in enumerate(lines):
                    ls = line.strip()
                    if not ls:
                        continue
                    compact = _compact(ls)
                    if amount is None and ('金额' in compact or '￥' in compact or '¥' in compact):
                        amount = _extract_amount_from_line(ls)

            if invoice_no is None:
                def find_contiguous_20digits(text):
                    buf = ''
                    for c in text:
                        if c.isdigit():
                            buf += c
                            if len(buf) == 20:
                                return buf
                        else:
                            buf = ''
                    return None
                for ls in lines:
                    ls = ls.strip()
                    if not ls:
                        continue
                    if '纳税人' in _compact(ls) or '信用代码' in _compact(ls):
                        continue
                    num = find_contiguous_20digits(ls)
                    if num:
                        invoice_no = num
                        break

            if amount is not None:
                file_name = os.path.basename(pdf_path)
                return {
                    'invoice_no': invoice_no or file_name.replace('.pdf', ''),
                    'seller_name': seller_name or '未知公司',
                    'amount': amount,
                    'file_path': pdf_path,
                    'file_name': file_name
                }
            return None
    except Exception as e:
        print(f"处理文件 {pdf_path} 时出错: {str(e)}")
        return None
