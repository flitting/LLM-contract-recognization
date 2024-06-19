import requests
import base64
import json
import io
import os
from PIL import Image
import math

API_KEY1 = 'L5g4SFgrJ5roC1wrcYDmIYWC'
SECRET_KEY1 = 'KeB0hEsckUjpF2q2XwB0E8OuCYgDSd1K'
API_KEY2 = 'fqmaM5zdzU27wNcLVtYpC71r'
SECRET_KEY2 = 'r2L4hIIU5f3Suxq5xiJUTUHnoDpjIuDC'


def get_access_token(api_key, secret_key):
    token_url = 'https://aip.baidubce.com/oauth/2.0/token'
    params = {
        'grant_type': 'client_credentials',
        'client_id': api_key,
        'client_secret': secret_key
    }
    response = requests.get(token_url, params=params)
    if response.status_code == 200:
        return response.json()['access_token']
    else:
        raise Exception('Failed to obtain access token')


def ocr_table(image_path, access_token):
    ocr_url = f'https://aip.baidubce.com/rest/2.0/ocr/v1/doc_analysis_office?access_token={access_token}'
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}

    with open(image_path, 'rb') as image_file:
        image_data = image_file.read()

    encoded_image_data = base64.b64encode(image_data).decode()
    payload = {
        'image': encoded_image_data,
        'recg_tables': 'true'
    }

    response = requests.post(ocr_url, headers=headers, data=payload)
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception('OCR request failed')


def generate_html_table(ocr_result, cells):
    if 'tables_result' not in ocr_result:
        raise Exception('No table data found in OCR result')

    tables_data = ocr_result['tables_result']
    html = "<html><body>"
    for table_index, table in enumerate(tables_data):
        rows = set()
        html += f"<h2>Table {table_index + 1}</h2>"
        html += "<table border='1'>"
        for cell in table['body']:
            colspan = cell['col_end'] - cell['col_start']
            rowspan = cell['row_end'] - cell['row_start']
            if cell['row_start'] not in rows:
                if cell["row_start"] - 1 in rows:
                    html += "</tr><tr>"
                else:
                    html += "<tr>"
                rows.add(cell['row_start'])
            html += f"<td rowspan='{rowspan}' colspan='{colspan}'>{cell['words']}</td>"
            cells[(table_index, cell['row_start'], cell['col_start'])] = [cell['words'], cell["cell_location"]]
        html += '</tr>'
        '''
            for row in table['body']:
            html += "<tr>"
            for cell in row['row']:
                content = cell['word']
                rowspan = cell.get('row_span', 1)
                colspan = cell.get('col_span', 1)
                html += f"<td rowspan='{rowspan}' colspan='{colspan}'>{content}</td>"
            html += "</tr>"
            
        '''
        html += "</table><br>"

    html += "</body></html>"
    return html


def call_wenxin_api(token, prompt):
    url = "https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/ernie-4.0-8k-latest?access_token=" + token
    headers = {
        'Content-Type': 'application/json'
    }
    data = json.dumps({
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ]
    })

    response = requests.post(url, headers=headers, data=data)
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception("API request failed")


if __name__ == '__main__':
    token1 = get_access_token(API_KEY1, SECRET_KEY1)
    token2 = get_access_token(API_KEY2, SECRET_KEY2)
    image_dir = 'input_images'
    html_dir = "output_html"
    base_prompt = "根据html表格内容，输出含义为含税总结额的纯数字，以JSON格式输出，无论何种情况，请仅按示例格式输出，输出你认为可能性最大的方案。示例{\"含税总金额\": 5481.50}"

    for filename in os.listdir(image_dir):
        cells = {}
        filepath = os.path.join(image_dir, filename)
        ocr_result = ocr_table(filepath, token1)
        #print(json.dumps(ocr_result, indent=4, ensure_ascii=False))
        html_table = generate_html_table(ocr_result, cells)

        #print(html_table)  # More reliable for various extensions
        result_path = os.path.join('output_html', filename[:-4] + ".html")

        with open(result_path, "w", encoding='utf-8') as f:
            f.write(html_table)
        prompt = base_prompt + html_table
        result = call_wenxin_api(token2, prompt)
        s = result['result'][8:-3]
        num = json.loads(s)['含税总金额']

        for i in cells:
            try:
                a = float(cells[i][0])
                if math.isclose(a, num):
                    break
            except ValueError:
                pass

        pos = cells[i][1]

        image = Image.open(filepath)

        for y in range(image.height):
            for x in range(image.width):
                if x > pos[0]['x'] and pos[2]['x']and y>pos[0]['y'] and y < pos[2]['y']:
                    colors = image.getpixel((x, y))
                    r = colors[0]
                    g = colors[1]
                    b = colors[2]
                    # 调整颜色以使色调偏黄
                    r = int(min(r * 1.5, 255))
                    g = int(min(g * 1.0, 255))
                    b = int(min(b * 0.5, 255))
                    image.putpixel((x, y), (r, g, b))
        image_path = os.path.join('output_images', filename[:-4]+'_highlighted.png')
        image.save(image_path)



