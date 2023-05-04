import json
import base64

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
      max-width: 100%;
    }
    td div svg {
      width: 100%;
      max-width: 100%;
    }
  </style>
</head>
<body>
"""

def to_svg(b64svg):
    b64svg = b64svg.replace('data:image/svg+xml;base64,', '')

    # decode the base64 encoded SVG
    svg_bytes = base64.b64decode(b64svg)

    # convert bytes to string
    svg_string = svg_bytes.decode('utf-8')

    # remove the XML declaration from the string
    svg_string = svg_string.replace('<?xml version="1.0" encoding="UTF-8" standalone="no"?>', '')

    # wrap the string in an inline <svg> tag
    return f'<div><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">{svg_string}</svg></div>'


# Generate HTML table
def plot_table(query, charts):
    html = f'<h4>{query}</h4>'
    html += '<table><thead><tr>'
    html += '<th>Type</th><th>Title</th><th>Source</th><th>SVG(b64)</th><th>SVG(orig)</th><th>Legend</th></tr>'
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
        svg_orig = ''
        if svg:
            svg_orig = to_svg(item['svg'])
        html += f"<tr><td>{item_type}</td><td>{title}</td><td>{sources}</td><td>{svg}</td><td>{svg_orig}</td><td>{legend}</td></tr>"
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

