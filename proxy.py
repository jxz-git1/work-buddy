"""
B站 API CORS 代理 - 零依赖
启动: python proxy.py
监听: http://localhost:8765
"""
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.request import Request, urlopen
from urllib.parse import urlparse, parse_qs
import json

class ProxyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = urlparse(self.path).path
        params = parse_qs(urlparse(self.path).query)

        # CORS 预检
        if self.command == 'OPTIONS':
            self.send_cors()
            self.end_headers()
            return

        if path == '/bilibili':
            bvid = params.get('bvid', [None])[0]
            if not bvid:
                self.send_json(400, {'code': -1, 'message': '缺少 bvid 参数'})
                return

            try:
                api_url = f'https://api.bilibili.com/x/web-interface/view?bvid={bvid}'
                req = Request(api_url, headers={
                    'User-Agent': 'Mozilla/5.0 Chrome/120.0.0.0',
                    'Referer': 'https://www.bilibili.com/',
                })
                resp = urlopen(req, timeout=10)
                data = json.loads(resp.read())

                if data.get('code') != 0:
                    self.send_json(502, data)
                    return

                d = data['data']
                pages = []
                for p in d.get('pages', []):
                    pages.append({
                        'page': p.get('page', 1),
                        'part': p.get('part', ''),
                        'duration': p.get('duration', 0),
                    })
                self.send_json(200, {
                    'code': 0,
                    'data': {
                        'bvid': d['bvid'],
                        'aid': d['aid'],
                        'title': d['title'],
                        'pic': d.get('pic', ''),
                        'desc': (d.get('desc', '') or '')[:200],
                        'owner': d.get('owner', {}).get('name', ''),
                        'duration': d.get('duration', 0),
                        'pages': pages,
                        'videos': d.get('videos', 1),
                    }
                })
            except Exception as e:
                self.send_json(502, {'code': -2, 'message': str(e)})
        else:
            self.send_json(404, {'code': -1, 'message': 'not found'})

    def do_OPTIONS(self):
        self.send_cors()
        self.end_headers()

    def send_cors(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', '*')
        self.send_header('Content-Type', 'application/json')

    def send_json(self, status, data):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))

    def log_message(self, format, *args):
        print(f"[proxy] {args[0]}")

if __name__ == '__main__':
    server = HTTPServer(('127.0.0.1', 8765), ProxyHandler)
    print('B站代理已启动 → http://localhost:8765/bilibili?bvid=BVxxx')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\n已停止')
        server.server_close()
