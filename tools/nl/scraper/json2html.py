import json

_IN_FILE = 'chart_cache.json'
_OUT_FILE = 'chart_cache.html'

HEADERS = ['Type', 'Title', 'Source', 'SVG', 'Legend']

_HTML = """
<!DOCTYPE html>
<html>
<head>
  <style>
    table {
      border-collapse: collapse;
    }
    th, td {
      border: 1px solid gray;
      text-align: left;
    }
    td div {
      border: 1px dotted gray;
    }
    td div img {
      width: 100%;
    }
  </style>
</head>
<body>
"""


# Generate HTML table
def plot_table(query, charts):
    html = f'<h4>{query}</h4>'
    html += '<table><thead><tr>'
    html += '<th>Type</th><th>Title</th><th>Source</th><th>SVG</th><th>Legend</th></tr>'
    html += '</thead><tbody>'
    for item in charts:
        item_type = item['type']
        title = item['title']
        legend = ''
        if 'legend' in item:
            legend = '<br>'.join(item['legend'])
        elif 'legend_svg' in item:
            legend = f"<div><img src=\"{item['legend_svg']}\" /></div>"
        sources = ''
        for src in item['srcs']:
            sources += f"<a href={src['url']}>{src['name']}</a>"
        svg = ''
        if 'svg' in item:
            svg = f"<div><img src=\"{item['svg']}\" /></div>"
        html += f"<tr><td>{item_type}</td><td>{title}</td><td>{sources}</td><td>{svg}</td><td>{legend}</td></tr>"
    html += "</tbody></table>\n"
    return html


with open(_IN_FILE) as f:
    query2charts = json.load(f)

html = _HTML
for q, charts in query2charts.items():
    html += plot_table(q, charts)
html += '</body></html>'

with open(_OUT_FILE, 'w') as  f:
    f.write(html)

