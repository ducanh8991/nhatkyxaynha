#!/usr/bin/env python3
"""Dựng website nhatkyxaynha.vn từ thư mục src/.

Cách dùng (chạy ở thư mục gốc của repo):
    python tools/build.py            # dựng toàn bộ trang + kiểm tra liên kết
    python tools/build.py --an-nhap  # dựng nhưng bỏ các bài còn là bản nháp (status "cho-duyet")

Chỉ dùng thư viện chuẩn của Python 3.8+. Kết quả là HTML tĩnh, commit lên nhánh main là GitHub Pages tự cập nhật.

Nguồn:
    src/site.json          chặng, truyện, công cụ, tình huống trang chủ
    src/hoi-nhanh.json     câu hỏi nhanh
    src/tu-dien.json       thuật ngữ
    src/stories/*.html     tranh cuộn + "Điều nằm lại" + câu hỏi của bé Na (giữ nguyên từ trang gốc)
    src/tools/*.html       giao diện công cụ (mặt sau của truyện)
    src/content/cam-nang/*.html, src/content/chuyen-sau/*.html   bài viết, đầu tệp có <!--meta {...}-->
    src/pages/*.html       trang chung, địa phương (cũng có <!--meta-->)
    src/partials/*         tranh trang chủ, biểu tượng chặng, gia đình trong truyện
    src/css/*.css, src/js/site.js
"""
import datetime
import hashlib
import html
import json
import os
import re
import sys
import unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'src')
HIDE_DRAFTS = '--an-nhap' in sys.argv

GENERATED = []          # đường dẫn tệp đã ghi, để kiểm tra
PAGES = {}              # url -> thông tin trang (dùng cho tìm kiếm, sitemap, liên kết)
WARN = []


# ---------------------------------------------------------------- tiện ích
def read(p):
    with open(os.path.join(SRC, p), encoding='utf-8') as f:
        t = f.read()
    if p.startswith('partials'):
        # Partial SVG được bọc trong <partial>…</partial> để công cụ chép tệp không coi nó là ảnh SVG.
        t = re.sub(r'^\s*<partial>\s*|\s*</partial>\s*$', '', t)
        t = re.sub(r'<metadata><c2pa:manifest>.*?</c2pa:manifest></metadata>', '', t, flags=re.S)
        t = re.sub(r'\s+xmlns:c2pa="[^"]*"', '', t)
    return t


def write(url_or_file, text):
    rel = url_or_file.lstrip('/')
    if rel == '' or rel.endswith('/'):
        rel += 'index.html'
    path = os.path.join(ROOT, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(text)
    GENERATED.append(rel)


def esc(s):
    return html.escape(str(s), quote=True)


def fold(s):
    s = unicodedata.normalize('NFD', str(s))
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return s.replace('đ', 'd').replace('Đ', 'D').lower()


def plain(htm):
    t = re.sub(r'<(script|style|svg)\b.*?</\1>', ' ', htm, flags=re.S)
    t = re.sub(r'<[^>]+>', ' ', t)
    return re.sub(r'\s+', ' ', html.unescape(t)).strip()


def load_meta(text, where):
    m = re.match(r'\s*<!--meta\s+(\{.*?\})\s*-->\s*', text, re.S)
    if not m:
        raise SystemExit('Thiếu <!--meta {...}--> ở đầu ' + where)
    try:
        meta = json.loads(m.group(1))
    except json.JSONDecodeError as e:
        raise SystemExit('Lỗi JSON trong meta của %s: %s' % (where, e))
    return meta, text[m.end():]


def asset_ver(paths):
    h = hashlib.sha1()
    for p in paths:
        with open(os.path.join(ROOT, p), 'rb') as f:
            h.update(f.read())
    return h.hexdigest()[:8]


# ---------------------------------------------------------------- dữ liệu
SITE = json.loads(read('site.json'))
CFG = SITE['site']
STAGES = {s['n']: s for s in SITE['stages']}
LAYERS = SITE['layers']
STORIES = SITE['stories']
STORY = {s['id']: s for s in STORIES}
TOOLS = SITE['tools']
TOOL = {t['slug']: t for t in TOOLS}
LEGACY = json.loads(read('partials/legacy-story-meta.json'))
ICONS = {int(k): v for k, v in json.loads(read('partials/stage-icons.json')).items()}
QUESTIONS = json.loads(read('hoi-nhanh.json')) if os.path.exists(os.path.join(SRC, 'hoi-nhanh.json')) else []
TERMS = json.loads(read('tu-dien.json')) if os.path.exists(os.path.join(SRC, 'tu-dien.json')) else []
TODAY = datetime.date.today().isoformat()
BANDO = json.loads(read('ban-do.json')) if os.path.exists(os.path.join(SRC, 'ban-do.json')) else {'stages': {}}
if HIDE_DRAFTS and BANDO.get('status') == 'cho-duyet':
    BANDO = {'stages': {}}

LAYER_LABEL = {l['key']: l['label'] for l in LAYERS}
STATUS_DRAFT = 'cho-duyet'


def code_key(code):
    m = re.match(r'([A-Z])(\d+)\.(\d+)', code or '')
    order = {'T': 0, 'C': 1, 'N': 2, 'S': 3}
    return (int(m.group(2)), order.get(m.group(1), 9), int(m.group(3))) if m else (99, 9, 99)


def load_articles(folder, layer):
    out = []
    d = os.path.join(SRC, 'content', folder)
    if not os.path.isdir(d):
        return out
    for fn in sorted(os.listdir(d)):
        if not fn.endswith('.html'):
            continue
        meta, body = load_meta(read(os.path.join('content', folder, fn)), fn)
        meta.setdefault('slug', fn[:-5])
        meta['layer'] = layer
        meta['url'] = '/%s/%s/' % (folder, meta['slug'])
        meta['body'] = body
        if HIDE_DRAFTS and meta.get('status') == STATUS_DRAFT:
            continue
        out.append(meta)
    out.sort(key=lambda a: code_key(a.get('code')))
    return out


ARTICLES = load_articles('cam-nang', 'cam-nang') + load_articles('chuyen-sau', 'chuyen-sau')
ART = {a['slug']: a for a in ARTICLES}

EXTRA = []
pdir = os.path.join(SRC, 'pages')
if os.path.isdir(pdir):
    for fn in sorted(os.listdir(pdir)):
        if fn.endswith('.html'):
            meta, body = load_meta(read(os.path.join('pages', fn)), fn)
            meta['body'] = body
            if HIDE_DRAFTS and meta.get('status') == STATUS_DRAFT:
                continue
            EXTRA.append(meta)


def story_url(sid): return '/chuyen/%s/' % sid
def tool_url(slug): return '/cong-cu/%s/' % slug
def stage_url(n): return '/chang/%d/' % n
def is_draft(x): return x.get('status') == STATUS_DRAFT


def stage_items(n):
    """Mọi nội dung của một chặng, theo tầng."""
    return {
        'truyen': [s for s in STORIES if s['stage'] == n],
        'lam-thu': [t for t in TOOLS if t['stage'] == n],
        'cam-nang': [a for a in ARTICLES if a['stage'] == n and a['layer'] == 'cam-nang'],
        'chuyen-sau': [a for a in ARTICLES if a['stage'] == n and a['layer'] == 'chuyen-sau'],
    }


def item_url(layer, it):
    if layer == 'truyen':
        return story_url(it['id'])
    if layer == 'lam-thu':
        return tool_url(it['slug'])
    return it['url']


# ---------------------------------------------------------------- từ điển trong bài
TERM_INDEX = []
for t in TERMS:
    for name in [t['term']] + t.get('aliases', []):
        TERM_INDEX.append((name, t))
TERM_INDEX.sort(key=lambda x: -len(x[0]))


def link_terms_safe(body):
    """Bản đơn giản, dễ đọc: duyệt từng đoạn chữ, thay lần đầu của mỗi thuật ngữ."""
    if not TERM_INDEX:
        return body
    done = set()
    parts = re.split(r'(<[^>]+>)', body)
    skip = 0
    skip_tags = ('a', 'h1', 'h2', 'h3', 'h4', 'summary', 'th', 'button', 'code', 'svg', 'dt')
    res = []
    for part in parts:
        if part.startswith('<'):
            m = re.match(r'<(/?)([a-zA-Z0-9]+)', part)
            if m and m.group(2).lower() in skip_tags and not part.endswith('/>'):
                skip += -1 if m.group(1) else 1
            res.append(part)
            continue
        if skip > 0 or not part.strip():
            res.append(part)
            continue
        changed = True
        while changed:
            changed = False
            for name, t in TERM_INDEX:
                if t['slug'] in done:
                    continue
                m = re.search(r'(?<![\w])(%s)(?![\w])' % re.escape(name), part, re.I)
                if not m:
                    continue
                done.add(t['slug'])
                a = '<a class="term" href="/tu-dien/#%s" data-term="%s" data-def="%s" aria-expanded="false">%s</a>' % (
                    t['slug'], esc(t['term']), esc(plain(t['def'])), m.group(1))
                res.append(part[:m.start()])
                res.append(a)
                part = part[m.end():]
                changed = True
                break
        res.append(part)
    return ''.join(res)


# ---------------------------------------------------------------- khung trang
CSS_FILES = sorted(f for f in os.listdir(os.path.join(SRC, 'css')) if f.endswith('.css'))
css = '\n'.join(read(os.path.join('css', f)) for f in CSS_FILES)
write('/assets/css/site.css', '/* Tệp sinh tự động từ src/css bởi tools/build.py. Sửa ở src/css. */\n' + css)
write('/assets/js/site.js', '/* Tệp sinh tự động từ src/js bởi tools/build.py. Sửa ở src/js. */\n' + read('js/site.js'))
VER = asset_ver(['assets/css/site.css', 'assets/js/site.js'])
SPRITE = read('partials/sprite.html')

ICON_SEARCH = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="M20 20l-4-4"/></svg>'
BRAND_SVG = '<svg viewBox="0 0 40 40" aria-hidden="true"><rect x="9" y="12" width="22" height="24" rx="2" fill="#F2D78E" stroke="#1E2A4C" stroke-width="2"/><path d="M6 14 L20 4 L34 14" fill="none" stroke="#C4553B" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/><rect x="16" y="24" width="8" height="12" fill="#2E7A66"/></svg>'

NAV = [('/ban-do/', '<span class="wide-only">Bản đồ </span>8 chặng', 'chang'), ('/hoi-nhanh/', 'Hỏi nhanh', 'hoi-nhanh'),
       ('/cong-cu/', 'Công cụ', 'cong-cu'), ('/tu-dien/', 'Từ điển', 'tu-dien')]


def header(section):
    links = []
    for href, label, key in NAV:
        cur = ' aria-current="page"' if section == key else ''
        links.append('<a href="%s"%s>%s</a>' % (href, cur, label))
    cur = ' aria-current="page"' if section == 'tim-kiem' else ''
    search = '<a class="nav-search" href="/tim-kiem/"%s>%sTìm</a>' % (cur, ICON_SEARCH)
    return ('<a class="skip" href="#noi-dung">Bỏ qua, đến nội dung</a>\n'
            '<header class="top">\n  <div class="wrap">\n'
            '    <a class="brand" href="/" aria-label="Nhật ký xây nhà, về trang đầu">%s Nhật ký xây nhà</a>\n'
            '    <nav class="nav" aria-label="Mục chính">%s</nav>\n    %s\n  </div>\n</header>\n') % (BRAND_SVG, ''.join(links), search)


def footer():
    return ('<footer>\n  <div class="wrap">\n'
            '    <div class="foot-col"><span>Nhân vật và con số trong truyện là hư cấu, chỉ để minh hoạ.</span>'
            '<span>Nội dung để tham khảo, không thay cho tư vấn của người có chuyên môn và cơ quan địa phương.</span></div>\n'
            '    <div class="foot-col"><nav class="foot-links" aria-label="Thông tin">'
            '<a href="/gioi-thieu/">Giới thiệu</a><a href="/danh-cho-kts-nha-thau/">Dành cho KTS và nhà thầu</a>'
            '<a href="/dia-phuong/">Theo địa phương</a><a href="/quyen-rieng-tu/">Quyền riêng tư</a></nav>'
            '<span>Nhật ký xây nhà · Một sản phẩm của Shanco</span></div>\n'
            '  </div>\n</footer>\n')


def layout(url, title, desc, main, kind, section='', page_title=None, kind_label='', draft=False,
           extra_head='', story=False, og_image=None, full_title=None):
    canonical = CFG['url'] + url
    t = full_title or ('%s · Nhật ký xây nhà' % title)
    robots = '<meta name="robots" content="noindex">\n' if draft or kind in ('404', 'search') else ''
    og = og_image or '/assets/img/og/mac-dinh.png'
    og_tag = ''
    if os.path.exists(os.path.join(ROOT, og.lstrip('/'))):
        og_tag = '<meta property="og:image" content="%s%s">\n' % (CFG['url'], og)
    PAGES[url] = PAGES.get(url, {})
    PAGES[url].update({'url': url, 'title': title, 'kind': kind, 'draft': draft})
    return ('<!doctype html>\n<html lang="vi">\n<head>\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
            '<title>%(t)s</title>\n<meta name="description" content="%(d)s">\n%(robots)s'
            '<link rel="canonical" href="%(c)s">\n'
            '<meta property="og:type" content="website">\n<meta property="og:site_name" content="Nhật ký xây nhà">\n'
            '<meta property="og:title" content="%(t)s">\n<meta property="og:description" content="%(d)s">\n'
            '<meta property="og:url" content="%(c)s">\n%(og)s'
            '<link rel="icon" href="data:image/svg+xml,%%3Csvg xmlns=\'http://www.w3.org/2000/svg\' viewBox=\'0 0 40 40\'%%3E%%3Crect x=\'9\' y=\'12\' width=\'22\' height=\'24\' rx=\'2\' fill=\'%%23F2D78E\' stroke=\'%%231E2A4C\' stroke-width=\'2\'/%%3E%%3Cpath d=\'M6 14 L20 4 L34 14\' fill=\'none\' stroke=\'%%23C4553B\' stroke-width=\'3\' stroke-linecap=\'round\'/%%3E%%3Crect x=\'16\' y=\'24\' width=\'8\' height=\'12\' fill=\'%%232E7A66\'/%%3E%%3C/svg%%3E">\n'
            '<link rel="preload" href="/assets/fonts/mali-vietnamese-600-normal.woff2" as="font" type="font/woff2" crossorigin>\n'
            '<link rel="stylesheet" href="/assets/css/site.css?v=%(v)s">\n%(extra)s'
            '</head>\n<body data-kind="%(kind)s" data-kind-label="%(kl)s" data-title="%(pt)s">\n'
            '%(progress)s%(sprite)s\n%(header)s<main id="noi-dung">\n%(main)s\n</main>\n%(footer)s'
            '<script src="/assets/js/site.js?v=%(v)s" defer></script>\n</body>\n</html>\n') % {
        't': esc(t), 'd': esc(desc), 'robots': robots, 'c': esc(canonical), 'og': og_tag, 'v': VER,
        'extra': extra_head, 'kind': kind, 'kl': esc(kind_label), 'pt': esc(page_title or title),
        'progress': '<div class="progress" id="progress" hidden><span></span></div>\n' if story else '',
        'sprite': SPRITE, 'header': header(section), 'main': main, 'footer': footer()}


def crumbs(items):
    out = ['<a href="/">Nhật ký xây nhà</a>']
    for label, href in items:
        out.append('<span class="sep" aria-hidden="true">›</span>')
        out.append('<a href="%s">%s</a>' % (href, esc(label)) if href else '<span aria-current="page">%s</span>' % esc(label))
    return '<nav aria-label="Bạn đang ở đây"><p class="crumbs">%s</p></nav>' % ''.join(out)


def ruler(n, here):
    items = stage_items(n)
    lis = []
    for l in LAYERS:
        k = l['key']
        urls = [item_url(k, it) for it in items[k]]
        cls = []
        if k == here:
            cls.append('is-here')
        if not urls:
            cls.append('is-empty')
        inner = '<i></i>%s' % l['label']
        if k == here:
            el = '<span aria-current="true">%s</span>' % inner
        elif urls:
            el = '<a href="%s#%s">%s</a>' % (stage_url(n), k, inner)
        else:
            el = '<span title="Chưa có bài">%s</span>' % inner
        lis.append('<li class="%s" data-urls="%s">%s</li>' % (' '.join(cls), '|'.join(urls), el))
    return ('<div><p class="ruler-label">Độ sâu của chặng %d</p><ol class="ruler" aria-label="Các tầng nội dung của chặng %d">%s</ol></div>'
            % (n, n, ''.join(lis)))


def way(small, title, href, em='', main=False):
    return ('<li><a class="way%s" href="%s"><small>%s</small><span>%s</span>%s</a></li>'
            % (' is-main' if main else '', href, esc(small), esc(title), '<em>%s</em>' % esc(em) if em else ''))


def ways(lst):
    lst = [w for w in lst if w]
    if not lst:
        return ''
    return '<nav class="ways" aria-label="Đi tiếp"><div class="wrap"><h2>Bạn muốn đi đâu tiếp?</h2><ul>%s</ul></div></nav>' % ''.join(lst)


def vn_date(iso):
    try:
        y, m, d = str(iso).split('-')
        return '%d/%d/%s' % (int(d), int(m), y)
    except ValueError:
        return esc(iso)


def draft_note(x):
    if not is_draft(x):
        return ''
    return ('<p class="draft"><b>Bản nháp, đang chờ chuyên gia rà soát.</b> Nội dung để tham khảo; '
            'hãy hỏi lại người có chuyên môn và cơ quan địa phương trước khi quyết định.</p>')


def review_line(x):
    if is_draft(x):
        return '<p class="review">Soạn ngày %s · Đang chờ duyệt chuyên môn.</p>' % vn_date(x.get('written', TODAY))
    bits = []
    if x.get('reviewer'):
        bits.append('Người duyệt: %s' % esc(x['reviewer']))
    if x.get('reviewed'):
        bits.append('Rà soát lần cuối: %s' % vn_date(x['reviewed']))
    if x.get('next_review'):
        bits.append('Rà soát tiếp: %s' % vn_date(x['next_review']))
    return '<p class="review">%s</p>' % ' · '.join(bits) if bits else ''


def sources_block(x):
    src = x.get('sources') or []
    if not src:
        return ''
    lis = ''.join('<li><a href="%s" rel="noopener">%s</a>%s</li>' % (esc(s['url']), esc(s['title']), (' · ' + esc(s['note'])) if s.get('note') else '') for s in src)
    return '<section class="sources"><h2>Nguồn tham khảo</h2><ol>%s</ol></section>' % lis


# ---------------------------------------------------------------- bản đồ, cổng chặng, sổ hành trình
def bando(n):
    return BANDO.get('stages', {}).get(str(n), {})


def stage_urls(n):
    items = stage_items(n)
    return [stage_url(n)] + [item_url(k, it) for k in ('truyen', 'lam-thu', 'cam-nang', 'chuyen-sau') for it in items[k]]


def gate_list(n):
    g = bando(n).get('gate', [])
    return ''.join('<li><label><input type="checkbox" data-gate="%d" data-i="%d"><span>%s</span></label></li>' % (n, i, esc(x))
                   for i, x in enumerate(g))


def gate_block(n):
    """Ô 'Cổng chặng' cuối trang chặng: danh sách đánh dấu, nhớ trong trình duyệt."""
    g = bando(n).get('gate', [])
    if not g:
        return ''
    nxt = ('<a href="%s">Sang chặng %d · %s →</a>' % (stage_url(n + 1), n + 1, esc(STAGES[n + 1]['label'])) if n < 8
           else '<a href="/ban-do/">Xem lại cả bản đồ →</a>')
    note = ' Phần này là bản nháp, đang chờ chuyên gia rà soát.' if BANDO.get('status') == STATUS_DRAFT else ''
    return ('<section class="gate-sec" id="cong-chang"><div class="wrap"><div class="gate" data-stage="%d" data-total="%d">'
            '<div class="gate-head"><p class="eyebrow">Cổng chặng %d</p><h2>Xong những việc này là sang chặng sau</h2>'
            '<p class="gate-count" data-stage="%d" aria-live="polite">0/%d việc</p></div>'
            '<ul class="gate-list">%s</ul>'
            '<p class="gate-done" hidden><b>Bạn đã qua cổng chặng %d.</b> Sổ hành trình đã đóng dấu. %s</p>'
            '<p class="gate-note">Đánh dấu chỉ lưu trong trình duyệt của bạn.%s</p>'
            '</div></div></section>') % (n, len(g), n, n, len(g), gate_list(n), n, nxt, note)


def catmull(points):
    d = 'M%.0f %.0f' % points[0]
    p = [points[0]] + points + [points[-1]]
    for i in range(1, len(p) - 2):
        p0, p1, p2, p3 = p[i - 1], p[i], p[i + 1], p[i + 2]
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        d += ' C%.0f %.0f, %.0f %.0f, %.0f %.0f' % (c1 + c2 + p2)
    return d


def map_counts(n):
    it = stage_items(n)
    bits = []
    if it['truyen']:
        bits.append('%d truyện' % len(it['truyen']))
    if it['lam-thu']:
        bits.append('%d công cụ' % len(it['lam-thu']))
    arts = len(it['cam-nang']) + len(it['chuyen-sau'])
    if arts:
        bits.append('%d bài' % arts)
    return ' · '.join(bits)


def map_svg():
    """Bản đồ vẽ nét: con đường uốn qua 8 chặng, hàng trên 1→4, vòng xuống, hàng dưới 5→8, về tới ngôi nhà."""
    stops = {1: (210, 150), 2: (480, 150), 3: (750, 150), 4: (1020, 150),
             5: (1020, 360), 6: (750, 360), 7: (480, 360), 8: (210, 360)}
    pts = [(40, 168), stops[1], (345, 128), stops[2], (615, 172), stops[3], (885, 128), stops[4],
           (1128, 196), (1128, 318), stops[5], (885, 382), stops[6], (615, 338), stops[7], (345, 382), stops[8], (112, 352)]
    road = catmull(pts)
    out = ['<svg class="map-art" viewBox="0 0 1200 480" role="group" aria-label="Bản đồ tám chặng: bấm vào một chặng để xem nội dung">',
           '<path d="M0 300 Q 200 262 420 286 T 860 282 T 1200 270 V480 H0Z" fill="#E4E9DA"/>',
           '<circle cx="1112" cy="58" r="30" fill="#F2D78E"/>',
           '<g fill="#FBFBF6"><ellipse cx="620" cy="52" rx="58" ry="17"/><ellipse cx="596" cy="42" rx="30" ry="16"/>'
           '<ellipse cx="96" cy="60" rx="46" ry="14"/><ellipse cx="118" cy="50" rx="26" ry="14"/></g>',
           '<g fill="#2E7A66"><rect x="343" y="82" width="4" height="14" fill="#8A6A44"/><circle cx="345" cy="76" r="12"/><circle cx="356" cy="82" r="8"/>'
           '<rect x="883" y="80" width="4" height="14" fill="#8A6A44"/><circle cx="885" cy="74" r="11"/>'
           '<rect x="613" y="298" width="4" height="14" fill="#8A6A44"/><circle cx="615" cy="292" r="11"/><circle cx="625" cy="298" r="7"/>'
           '<rect x="1160" y="246" width="4" height="14" fill="#8A6A44"/><circle cx="1162" cy="240" r="11"/></g>',
           '<path d="%s" fill="none" stroke="#FBFBF6" stroke-width="24" stroke-linecap="round" stroke-linejoin="round"/>' % road,
           '<path class="road-dash" d="%s" fill="none" stroke="#56607B" stroke-width="2" stroke-dasharray="10 12"/>' % road,
           # gia đình ở điểm xuất phát
           '<g stroke="#1E2A4C" stroke-width="1.5"><circle cx="30" cy="140" r="6" fill="#1E2A4C"/><rect x="25" y="147" width="10" height="16" rx="4" fill="#C4553B"/>'
           '<circle cx="46" cy="148" r="4.5" fill="#1E2A4C"/><rect x="42" y="153" width="8" height="11" rx="3" fill="#E6B53C"/></g>',
           # ngôi nhà ở cuối đường
           '<g stroke="#1E2A4C" stroke-width="2" stroke-linejoin="round"><rect x="52" y="292" width="54" height="64" fill="#F2D78E"/>'
           '<path d="M44 296 L79 268 L114 296Z" fill="#C4553B"/><rect x="72" y="326" width="14" height="30" fill="#2E7A66"/>'
           '<rect x="60" y="302" width="12" height="12" fill="#FBFBF6" stroke-width="1.5"/><rect x="88" y="302" width="12" height="12" fill="#FBFBF6" stroke-width="1.5"/></g>']
    for n in range(1, 9):
        x, y = stops[n]
        st = STAGES[n]
        icon = ICONS[n].replace('<svg ', '<svg x="%d" y="%d" width="34" height="34" ' % (x - 17, y - 17), 1)
        out.append(
            '<a class="map-stop" href="#chang-%d" data-stage="%d" aria-label="Chặng %d: %s, %s">'
            '<circle class="ms-ring" cx="%d" cy="%d" r="34"/>'
            '<g class="ms-ico" style="color:#1E2A4C">%s</g>'
            '<circle cx="%d" cy="%d" r="13" fill="#E6B53C" stroke="#1E2A4C" stroke-width="2"/>'
            '<text class="ms-n" x="%d" y="%d">%d</text>'
            '<g class="ms-stamp"><circle cx="%d" cy="%d" r="12" fill="#2E7A66" stroke="#1E2A4C" stroke-width="2"/>'
            '<path d="M%d %d l4 4 l8 -9" fill="none" stroke="#FBFBF6" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"/></g>'
            '<text class="ms-label" x="%d" y="%d">%s</text>'
            '<text class="ms-poetic" x="%d" y="%d">%s</text>'
            '<text class="ms-count" x="%d" y="%d">%s</text></a>'
            % (n, n, n, esc(st['label']), esc(st['poetic']), x, y, icon,
               x - 27, y - 27, x - 27, y - 22, n,
               x + 27, y - 27, x + 21, y - 27,
               x, y + 60, esc(st['label']), x, y + 81, esc(st['poetic']), x, y + 100, esc(map_counts(n))))
    out.append('</svg>')
    return ''.join(out)


PANEL_ICONS = {
    'decisions': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M8 12l3 3 5-6"/></svg>',
    'mistakes': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 3l9 16H3z"/><path d="M12 10v4M12 17v.5"/></svg>',
    'papers': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M7 3h7l4 4v14H7z"/><path d="M14 3v4h4M10 12h5M10 16h5"/></svg>',
    'gate': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 21V9l8-5 8 5v12"/><path d="M9 21v-7h6v7"/></svg>',
}
PANEL_TITLES = [('decisions', 'Quyết định chính'), ('mistakes', 'Sai lầm hay gặp'), ('papers', 'Giấy tờ cần có'), ('gate', 'Cổng chặng')]


def build_map():
    stats = '%d chặng · %d truyện · %d công cụ · %d bài cẩm nang · %d bài chuyên sâu · %d câu hỏi nhanh' % (
        8, len(STORIES), len(TOOLS), len([a for a in ARTICLES if a['layer'] == 'cam-nang']),
        len([a for a in ARTICLES if a['layer'] == 'chuyen-sau']), len(QUESTIONS))
    grid = ''.join('<li><a class="mg-stop" href="#chang-%d" data-stage="%d"><span class="mg-ico">%s</span><span class="mg-n">%d</span>'
                   '<span class="mg-l">%s</span><span class="mg-c">%s</span></a></li>'
                   % (n, n, ICONS[n], n, esc(STAGES[n]['label']), esc(map_counts(n))) for n in range(1, 9))
    jump = ''.join('<a href="#chang-%d" data-stage="%d" title="Chặng %d · %s">%d</a>' % (n, n, n, esc(STAGES[n]['label']), n) for n in range(1, 9))
    secs = []
    has_panels = any(bando(n) for n in range(1, 9))
    for n in range(1, 9):
        st = STAGES[n]
        items = stage_items(n)
        groups = []
        for l in LAYERS:
            k = l['key']
            lst = items[k]
            if not lst:
                continue
            lis = ''.join('<li><a href="%s">%s</a></li>' % (item_url(k, it), esc(it.get('title') or it.get('name'))) for it in lst)
            groups.append('<div class="mc-group mc-%s"><h3>%s <small>%d</small></h3><ul>%s</ul></div>' % (k, l['label'], len(lst), lis))
        qn = len([q for q in QUESTIONS if q.get('stage') == n])
        if qn:
            groups.append('<div class="mc-group mc-hoi"><h3>Hỏi nhanh <small>%d</small></h3><ul><li><a href="/hoi-nhanh/#chang-%d">%d câu hỏi hay gặp ở chặng này</a></li></ul></div>' % (qn, n, qn))
        panels = ''
        b = bando(n)
        if b:
            ps = []
            for key, title in PANEL_TITLES:
                lst = b.get(key) or []
                if not lst:
                    continue
                if key == 'gate':
                    body = ('<ul class="gate-list">%s</ul><p class="gate-done" hidden><b>Đã qua cổng.</b> Sổ hành trình đã đóng dấu chặng %d.</p>' % (gate_list(n), n))
                    cnt = '<small class="gate-count" data-stage="%d">0/%d</small>' % (n, len(lst))
                else:
                    body = '<ul>%s</ul>' % ''.join('<li>%s</li>' % esc(x) for x in lst)
                    cnt = '<small>%d</small>' % len(lst)
                ps.append('<details class="mpanel mp-%s"%s><summary><span class="mp-ico">%s</span><span class="mp-t">%s</span>%s</summary><div class="mp-body">%s</div></details>'
                          % (key, ' data-stage="%d" data-total="%d"' % (n, len(lst)) if key == 'gate' else '', PANEL_ICONS[key], title, cnt, body))
            panels = '<div class="mpanels">%s</div>' % ''.join(ps)
        secs.append(
            '<section class="mstage" id="chang-%d" data-stage="%d" data-urls="%s"><div class="mstage-head">'
            '<span class="mstage-pin">%d</span><span class="ico-wrap">%s</span>'
            '<div class="mstage-title"><p class="station-label">Chặng %d · %s</p><h2>%s</h2></div>'
            '<span class="mstage-state" data-stage="%d"></span></div>'
            '<p class="mstage-intro">%s</p>'
            '<div class="mstage-body"><div class="mcontent"><p class="mc-cap">Đọc gì, dùng gì</p>%s'
            '<a class="station-more" href="%s">Mở trang chặng %d →</a></div>%s</div></section>'
            % (n, n, '|'.join(stage_urls(n)), n, ICONS[n], n, esc(st['label']), esc(st['poetic']), n, esc(st['intro']), ''.join(groups), stage_url(n), n, panels))
    note = ''
    if has_panels and BANDO.get('status') == STATUS_DRAFT:
        note = ('<p class="draft"><b>Bản nháp, đang chờ chuyên gia rà soát.</b> Các mục Quyết định chính, Sai lầm hay gặp, Giấy tờ cần có, '
                'Cổng chặng rút từ các bài cẩm nang; hãy hỏi lại người có chuyên môn và cơ quan địa phương trước khi quyết định.</p>')
    tools_bar = ('<div class="map-tools"><button class="btn" type="button" id="map-expand" aria-pressed="false">Mở hết các mục</button>'
                 '<button class="btn" type="button" id="map-print">In bản đồ</button></div>') if has_panels else ''
    main = ('<header class="page-head map-head"><div class="wrap">%s<p class="eyebrow">Bản đồ hành trình</p>'
            '<h1>Toàn cảnh tám chặng xây nhà</h1>'
            '<p class="stage-intro">Bấm vào một chặng để xem chặng đó có gì: đọc truyện nào, dùng công cụ nào, phải quyết định gì, cần giấy tờ gì và khi nào thì sang chặng sau.</p>'
            '<p class="map-stats">%s</p></div></header>'
            '<section class="map-sec"><div class="wrap"><nav aria-label="Bản đồ tám chặng">%s<ol class="map-grid">%s</ol></nav>'
            '<p class="map-legend"><span class="lg-done"></span> Chặng đã qua cổng <span class="lg-seen"></span> Chặng đã đọc vài bài</p></div></section>'
            '<nav class="map-jump" aria-label="Nhảy tới chặng"><div class="wrap"><span>Chặng</span>%s</div></nav>'
            '<div class="wrap map-list">%s%s%s</div>') % (
        crumbs([('Bản đồ hành trình', None)]), stats, map_svg(), grid, jump, note, tools_bar, ''.join(secs))
    write('/ban-do/', layout('/ban-do/', 'Bản đồ hành trình', 'Toàn cảnh tám chặng xây nhà lần đầu trên một trang: truyện, công cụ, cẩm nang, quyết định chính, sai lầm hay gặp, giấy tờ cần có ở từng chặng.',
                             main, 'ban-do', section='chang', kind_label='Bản đồ'))
    PAGES['/ban-do/'].update({'search': {'k': 'trang', 'c': 'Bản đồ hành trình', 's': 'Toàn cảnh tám chặng trên một trang.',
                                         'x': 'ban do hanh trinh tong quan tam chang ' + ' '.join(STAGES[n]['label'] for n in range(1, 9))}})


def passport_block():
    lis = []
    for n in range(1, 9):
        st = STAGES[n]
        lis.append('<li class="stamp" data-stage="%d" data-urls="%s" data-total="%d"><a href="/ban-do/#chang-%d">'
                   '<span class="stamp-ring">%s</span><span class="stamp-n">Chặng %d</span><span class="stamp-l">%s</span>'
                   '<span class="stamp-s">Chưa đi</span></a></li>'
                   % (n, '|'.join(stage_urls(n)), len(bando(n).get('gate', [])), n, ICONS[n], n, esc(st['label'])))
    return ('<section class="sec" id="so-hanh-trinh"><div class="wrap"><div class="passport">'
            '<div class="passport-head"><p class="eyebrow">Sổ hành trình của bạn</p><h2>Những chặng bạn đã đi qua</h2>'
            '<p id="passport-text" data-stories="%d">Chưa có dấu nào. Đọc một câu chuyện hoặc đánh dấu Cổng chặng cuối mỗi trang chặng để nhận dấu đầu tiên.</p></div>'
            '<ol class="stamps">%s</ol>'
            '<p class="passport-note">Dấu nhạt: bạn đã đọc bài của chặng. Dấu đậm: bạn đã qua Cổng chặng. Sổ chỉ lưu trong trình duyệt này, không gửi đi đâu. '
            '<button type="button" class="link-btn" id="passport-reset">Xoá sổ</button></p>'
            '</div></div></section>') % (len(STORIES), ''.join(lis))


# ---------------------------------------------------------------- trang chủ
def build_home():
    hero = read('partials/hero-art.html')
    where = ''.join('<a class="where-opt" href="%s" data-label="%s">%s</a>' % (stage_url(s['stage']), esc(s['label']), esc(s['label']))
                    for s in SITE['situations'])
    sugg = ' · '.join('<a href="/tim-kiem/?q=%s">%s</a>' % (esc(q), esc(q)) for q in SITE['search_suggestions'])
    quick = ''.join('<li>%s</li>' % item_card('lam-thu', TOOL[s]) for s in SITE['quick_tools'])
    stations = []
    for n in range(1, 9):
        st = STAGES[n]
        tales = ''.join(
            '<li><a class="tale" href="%s"><span class="tale-topic">%s</span><span class="tale-title">%s</span>'
            '<span class="tale-hook">%s</span><span class="badge">Đọc · 2 phút</span></a></li>'
            % (story_url(s['id']), esc(s['topic']), esc(s['title']), esc(s['hook'])) for s in STORIES if s['stage'] == n)
        items = stage_items(n)
        cnt = len(items['cam-nang']) + len(items['chuyen-sau'])
        more = 'Xem cả chặng: %d công cụ%s →' % (len(items['lam-thu']), (', %d bài cẩm nang' % cnt) if cnt else '')
        stations.append(
            '<li class="station" id="tram-%d"><div class="pin">%d</div><div class="station-card">'
            '<div class="station-top"><span class="ico-wrap">%s</span><div><p class="station-label">Chặng %d · %s</p>'
            '<h3><a href="%s">%s</a></h3></div></div><ul class="tales">%s</ul>'
            '<a class="station-more" href="%s">%s</a></div></li>'
            % (n, n, ICONS[n], n, esc(st['label']), stage_url(n), esc(st['poetic']), tales, stage_url(n), more))
    main = '''<section class="hero">
  <div class="wrap">
    <div class="hero-text">
      <p class="eyebrow">Chuyện xây nhà lần đầu</p>
      <h1>Mỗi ngôi nhà là một <em>hành trình vui</em></h1>
      <p class="lede">Mười hai câu chuyện hai phút cho người lần đầu xây nhà, từ lúc cả nhà ngồi bàn đến khi ở nhà mới. Mỗi chuyện kèm một công cụ nhỏ để áp dụng cho nhà mình.</p>
      <p class="lede-note">Miễn phí, không cần đăng ký.</p>
      <div class="welcome" id="welcome" hidden><p id="welcome-text"></p><button type="button" id="welcome-reset">Bắt đầu lại</button></div>
      <div class="where">
        <h2>Nhà bạn đang ở đâu?</h2>
        <p>Chọn một, chúng tôi đưa bạn tới đúng chặng.</p>
        <div class="where-opts">%(where)s</div>
      </div>
      <form class="searchbox" action="/tim-kiem/" method="get" role="search">
        <label class="sr-only" for="home-q">Bạn đang tìm gì?</label>
        <input id="home-q" name="q" type="search" placeholder="Bạn đang tìm gì? Ví dụ: xin phép, báo giá…" autocomplete="off">
        <button class="btn btn-solid" type="submit">Tìm</button>
      </form>
      <p class="suggest"><span>Hay hỏi:</span> %(sugg)s</p>
      <p class="hero-more">Hoặc <a href="%(first)s">đọc chuyện đầu tiên</a> · <a href="/ban-do/">xem bản đồ tám chặng</a></p>
    </div>
    %(hero)s
  </div>
</section>

<section class="sec" id="cong-cu-nhanh">
  <div class="wrap">
    <div class="sec-head"><p class="eyebrow">Công cụ nhanh</p><h2>Dùng ngay, không cần đọc trước</h2>
    <p>Số liệu bạn nhập chỉ nằm trong trình duyệt của bạn. <a href="/cong-cu/">Xem cả 12 công cụ</a>.</p></div>
    <ul class="quick">%(quick)s</ul>
  </div>
</section>

<section class="sec" id="ban-do">
  <div class="wrap">
    <div class="sec-head">
      <p class="eyebrow">Bản đồ hành trình</p>
      <h2>Tám chặng, mười hai câu chuyện</h2>
      <p>Đi theo thứ tự cũng được, nhảy cóc cũng được. Mỗi chặng là một quãng đường mà nhà nào xây nhà cũng đi qua.</p>
    </div>
    <ol class="route">%(stations)s</ol>
    <p class="route-more"><a class="btn btn-solid" href="/ban-do/">Mở bản đồ đầy đủ: mọi bài, mọi công cụ, từng việc cần xong →</a></p>
  </div>
</section>
%(passport)s

<section class="sec" id="gia-dinh">
  <div class="wrap">
    <div class="sec-head">
      <p class="eyebrow">Gia đình trong truyện</p>
      <h2>Những người đi cùng bạn</h2>
      <p>Mọi câu chuyện xoay quanh một gia đình đang xây ngôi nhà đầu tiên, cùng người thợ và người hàng xóm của họ. Nhân vật là hư cấu.</p>
    </div>
    %(family)s
  </div>
</section>

<section class="sec" id="danh-cho-nghe">
  <div class="wrap">
    <div class="roles">
      <div><h2>Bạn là kiến trúc sư hoặc nhà thầu?</h2><p>Xem trang này giúp gì cho công việc của bạn và chủ nhà bạn đang làm cùng.</p></div>
      <a class="btn" href="/danh-cho-kts-nha-thau/">Dành cho KTS và nhà thầu →</a>
    </div>
  </div>
</section>

<section class="sec" id="ke-chuyen">
  <div class="wrap">
    <div class="tell">
      <div>
        <p class="eyebrow">Góc kể chuyện</p>
        <h2>Nhà bạn cũng có một câu chuyện?</h2>
        <p>Một lần cãi nhau vì cái cầu thang, một bữa cơm với thợ, một bài học nhớ đời. Những câu chuyện thật của người đọc sẽ được kể lại ở đây.</p>
      </div>
      <p class="tell-note">Góc kể chuyện sẽ sớm mở. Mỗi câu chuyện chỉ được đăng khi người kể đồng ý, và có thể giấu tên.</p>
    </div>
  </div>
</section>''' % {'where': where, 'sugg': sugg, 'quick': quick, 'stations': ''.join(stations), 'hero': hero,
                 'family': read('partials/family.html'), 'passport': passport_block(), 'first': story_url(STORIES[0]['id'])}
    redirect = {s['id']: story_url(s['id']) for s in STORIES}
    redirect.update({'chang-%d' % n: stage_url(n) for n in range(1, 9)})
    redirect['home'] = '/'
    head = ('<script>(function(){var m=%s;var h=location.hash.slice(1);if(m[h]&&m[h]!=="/")location.replace(m[h]);})();</script>\n'
            '<style>.sr-only{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap}</style>\n'
            % json.dumps(redirect, ensure_ascii=False))
    write('/', layout('/', 'Hành trình ngôi nhà', CFG['description'], main, 'home', full_title=CFG['home_title'], extra_head=head))
    PAGES['/']['search'] = None


def item_card(layer, it, with_stage=False):
    if layer == 'truyen':
        k, t, p, m = it['topic'], it['title'], it['hook'], 'Truyện · 2 phút'
    elif layer == 'lam-thu':
        k = 'Công cụ' + (' · Chặng %d' % it['stage'] if with_stage else '')
        t, p, m = it['name'], it['when'], 'Làm thử'
    else:
        k = LAYER_LABEL[layer] + (' · Chặng %d' % it['stage'] if with_stage else '')
        t, p, m = it['title'], 'Bạn sẽ biết: ' + it['learn'], '%s · %d phút đọc' % (LAYER_LABEL[layer], it.get('read', 5))
    cls = ' is-draft' if is_draft(it) else ''
    return ('<a class="item%s" href="%s"><span class="k">%s</span><span class="t">%s</span><span class="p">%s</span><span class="m">%s</span></a>'
            % (cls, item_url(layer, it), esc(k), esc(t), esc(p), esc(m)))


# ---------------------------------------------------------------- trang chặng
def build_stages():
    for n in range(1, 9):
        st = STAGES[n]
        items = stage_items(n)
        secs = []
        for l in LAYERS:
            k = l['key']
            lst = items[k]
            if lst:
                body = '<ul class="items">%s</ul>' % ''.join('<li>%s</li>' % item_card(k, it) for it in lst)
            else:
                body = '<p class="empty">Chưa có bài %s cho chặng này. Chúng tôi đang viết.</p>' % l['label'].lower()
            secs.append('<section class="layer-sec" id="%s"><div class="wrap"><div class="layer-head"><h2>%s</h2><p>%s</p></div>%s</div></section>'
                        % (k, l['label'], esc(l['desc']), body))
        qs = [q for q in QUESTIONS if q.get('stage') == n]
        if qs:
            secs.append('<section class="layer-sec" id="hoi-nhanh"><div class="wrap"><div class="layer-head"><h2>Hỏi nhanh</h2>'
                        '<p>Câu hỏi hay gặp ở chặng này.</p></div><ul class="qa">%s</ul></div></section>' % ''.join(qa_item(q) for q in qs))
        prev_ = '<a class="back" href="%s">← Chặng %d · %s</a>' % (stage_url(n - 1), n - 1, esc(STAGES[n - 1]['label'])) if n > 1 else '<a class="back" href="/ban-do/">← Bản đồ tám chặng</a>'
        next_ = ('<a class="next-card" href="%s"><small>Chặng tiếp theo</small><span>%d · %s →</span></a>' % (stage_url(n + 1), n + 1, esc(STAGES[n + 1]['label']))
                 if n < 8 else '<a class="next-card" href="/ban-do/"><small>Hết tám chặng</small><span>Về bản đồ →</span></a>')
        main = ('<header class="page-head"><div class="wrap">%s<p class="eyebrow">Chặng %d · %s</p><h1>%s</h1><p class="sub">%s</p>'
                '<p class="stage-intro">%s</p>%s</div></header>%s'
                '<div class="wrap"><div class="stage-nav">%s%s</div></div>') % (
            crumbs([('Chặng %d · %s' % (n, st['label']), None)]), n, esc(st['poetic']), esc(st['label']), esc(st['poetic']),
            esc(st['intro']), ruler(n, None), ''.join(secs) + gate_block(n), prev_, next_)
        url = stage_url(n)
        write(url, layout(url, 'Chặng %d · %s' % (n, st['label']), st['intro'], main, 'chang', section='chang', kind_label='Chặng'))
        PAGES[url].update({'search': {'k': 'chang', 'c': 'Chặng %d' % n, 's': st['intro'], 'x': st['label'] + ' ' + st['poetic'] + ' ' + st['intro']}})


def qa_item(q, show_stage=False):
    go = ''
    if q.get('link'):
        target = q['link']
        label = q.get('link_label') or 'Đọc kỹ hơn'
        go = '<p class="go"><a href="%s">%s →</a></p>' % (target, esc(label))
    st = ''
    if show_stage and q.get('stage'):
        st = ''
    return '<li id="%s"><h3>%s</h3><p>%s</p>%s</li>' % (q['slug'], esc(q['q']), q['a'], go)


# ---------------------------------------------------------------- truyện
def next_in(lst, cur, key):
    ids = [x[key] for x in lst]
    i = ids.index(cur)
    return lst[i + 1] if i + 1 < len(lst) else None


def build_stories():
    for s in STORIES:
        n = s['stage']
        st = STAGES[n]
        lg = LEGACY[s['id']]
        src = read('stories/%s.html' % s['id'])
        scrolly, end = src.split('<!--STORY-END-->')
        tool = TOOL[s['tool']]
        flip = ('<div class="flip"><div class="flip-front"><div><h3>Lật mặt sau: %s</h3><p>%s</p></div>'
                '<button class="btn btn-solid flip-btn" type="button" aria-expanded="false" aria-controls="%s">Lật mặt sau</button></div>'
                '<div class="flip-back" id="%s" hidden>%s</div></div>') % (
            esc(lg['tool_name_poetic']), lg['tool_desc'], lg['back_id'], lg['back_id'], read('tools/%s.html' % tool['slug']))
        nxt = next_in(STORIES, s['id'], 'id')
        deeper = ART.get(s.get('deeper'))
        w = [
            way('Đi sâu hơn · Cẩm nang', deeper['title'], deeper['url'], 'Bạn sẽ biết: ' + deeper['learn'], main=True) if deeper else None,
            way('Chuyện tiếp theo · Chặng %d' % nxt['stage'], nxt['title'], story_url(nxt['id']), nxt['topic']) if nxt else way('Hết mười hai chuyện', 'Về bản đồ tám chặng', '/ban-do/'),
            way('Làm thử ở trang riêng', tool['name'], tool_url(tool['slug']), tool['when']),
        ]
        main = ('<article class="story" id="%s">\n<header class="story-head"><div class="wrap">%s%s<p class="eyebrow">Chặng %d · %s</p>'
                '<h1>%s</h1><p class="learn"><span class="learn-topic">%s</span> <b>Bạn sẽ biết:</b> %s</p>'
                '<div class="meta"><span>%s</span><span>%s</span><span>%s</span><span class="kbd-hint">Dùng phím ↓ ↑ hoặc phím cách để chuyển cảnh</span></div></div></header>\n%s\n'
                '<div class="story-end"><div class="wrap">%s\n%s</div></div>\n</article>\n%s') % (
            s['id'], crumbs([('Chặng %d · %s' % (n, st['label']), stage_url(n)), (s['title'], None)]), ruler(n, 'truyen'),
            n, esc(st['label']), esc(s['title']), esc(s['topic']), esc(s['learn']),
            lg['read'], lg['cast'], lg['hint'], scrolly.strip(), end.strip(), flip, ways(w))
        url = story_url(s['id'])
        og = '/assets/img/og/%s.png' % s['id']
        write(url, layout(url, s['title'], '%s. Bạn sẽ biết %s' % (s['topic'], s['learn']), main, 'truyen', section='chang',
                          kind_label='Truyện', story=True, og_image=og))
        PAGES[url].update({'search': {'k': 'truyen', 'c': 'Truyện · Chặng %d · %s' % (n, s['topic']), 's': s['hook'],
                                      'x': ' '.join([s['title'], s['topic'], s['learn'], plain(src)[:1500]])}})


# ---------------------------------------------------------------- công cụ
def build_tools():
    cards = []
    for n in range(1, 9):
        lst = [t for t in TOOLS if t['stage'] == n]
        if lst:
            cards.append('<section class="layer-sec"><div class="wrap"><div class="layer-head"><h2>Chặng %d · %s</h2></div><ul class="items">%s</ul></div></section>'
                         % (n, esc(STAGES[n]['label']), ''.join('<li>%s</li>' % item_card('lam-thu', t) for t in lst)))
    main = ('<header class="page-head"><div class="wrap">%s<p class="eyebrow">Làm thử</p><h1>Công cụ</h1>'
            '<p class="stage-intro">Mười hai công cụ nhỏ, mỗi chặng một vài cái. Số liệu bạn nhập chỉ nằm trong trình duyệt của bạn, không gửi đi đâu.</p></div></header>%s'
            % (crumbs([('Công cụ', None)]), ''.join(cards)))
    write('/cong-cu/', layout('/cong-cu/', 'Công cụ', 'Mười hai công cụ nhỏ cho người lần đầu xây nhà: ước ngân sách, có cần xin phép, so báo giá, hợp đồng, nhật ký, nhận nhà.', main, 'trang', section='cong-cu'))
    for t in TOOLS:
        n = t['stage']
        s = STORY[t['story']]
        deeper = ART.get(s.get('deeper'))
        nxt = next_in(TOOLS, t['slug'], 'slug')
        note = '<p class="tool-note">%s</p>' % esc(t['review_note']) if t.get('review_note') else ''
        w = [
            way('Đọc truyện · 2 phút', s['title'], story_url(s['id']), s['topic']),
            way('Đi sâu hơn · Cẩm nang', deeper['title'], deeper['url'], 'Bạn sẽ biết: ' + deeper['learn'], main=True) if deeper else None,
            way('Công cụ tiếp theo · Chặng %d' % nxt['stage'], nxt['name'], tool_url(nxt['slug']), nxt['when']) if nxt else None,
        ]
        sub = '<p class="sub">%s</p>' % esc(t['poetic']) if t.get('poetic') else ''
        main = ('<header class="page-head"><div class="wrap">%s%s<p class="eyebrow">Làm thử · Chặng %d · %s</p><h1>%s</h1>%s'
                '<p class="tool-when"><b>Dùng khi:</b> %s</p></div></header>'
                '<section class="article"><div class="wrap"><p class="lede">%s</p><div class="tool-box"><div class="flip-back">%s</div></div>'
                '<p class="tool-note">Công cụ chỉ để hình dung và tự kiểm tra, không thay cho dự toán, tư vấn của người có chuyên môn hay ý kiến của cơ quan địa phương.</p>%s</div></section>%s') % (
            crumbs([('Chặng %d · %s' % (n, STAGES[n]['label']), stage_url(n)), ('Công cụ', '/cong-cu/'), (t['name'], None)]),
            ruler(n, 'lam-thu'), n, esc(STAGES[n]['label']), esc(t['name']), sub, esc(t['when']), t['desc'],
            read('tools/%s.html' % t['slug']), note, ways(w))
        url = tool_url(t['slug'])
        write(url, layout(url, t['name'], '%s Dùng khi: %s' % (plain(t['desc']), t['when']), main, 'cong-cu', section='cong-cu', kind_label='Công cụ'))
        PAGES[url].update({'search': {'k': 'cong-cu', 'c': 'Công cụ · Chặng %d' % n, 's': t['when'], 'x': ' '.join([t['name'], t.get('poetic', ''), t['when'], plain(t['desc'])])}})


# ---------------------------------------------------------------- bài cẩm nang, chuyên sâu
def build_articles():
    for a in ARTICLES:
        n = a['stage']
        layer = a['layer']
        same = [x for x in ARTICLES if x['layer'] == layer]
        nxt = next_in(same, a['slug'], 'slug')
        deeper = ART.get(a.get('deeper'))
        back = ART.get(a.get('back'))
        tool = TOOL.get(a.get('try'))
        w = [
            way('Đi sâu hơn · Chuyên sâu', deeper['title'], deeper['url'], 'Bạn sẽ biết: ' + deeper['learn'], main=True) if deeper else None,
            way('Quay lại · Cẩm nang', back['title'], back['url'], 'Bạn sẽ biết: ' + back['learn']) if back else None,
            way('Làm thử', tool['name'], tool_url(tool['slug']), tool['when']) if tool else None,
            way('Bài tiếp theo · %s · Chặng %d' % (LAYER_LABEL[layer], nxt['stage']), nxt['title'], nxt['url'], 'Bạn sẽ biết: ' + nxt['learn'], main=not deeper) if nxt else way('Hết bài %s' % LAYER_LABEL[layer].lower(), 'Về bản đồ tám chặng', '/ban-do/'),
        ]
        tldr = ''
        if a.get('tldr'):
            tldr = '<section class="tldr" aria-label="Tóm tắt 30 giây"><h2>Tóm tắt 30 giây</h2><ul>%s</ul></section>' % ''.join('<li>%s</li>' % x for x in a['tldr'])
        body = link_terms_safe(a['body'])
        main = ('<header class="page-head"><div class="wrap">%s%s<p class="eyebrow">%s · Chặng %d · %s</p><h1>%s</h1>'
                '<p class="learn"><b>Bạn sẽ biết:</b> %s</p><div class="meta"><span>%d phút đọc</span>%s</div>%s</div></header>'
                '<article class="article"><div class="wrap">%s<div class="prose">%s</div>%s%s</div></article>%s') % (
            crumbs([('Chặng %d · %s' % (n, STAGES[n]['label']), stage_url(n)), (LAYER_LABEL[layer], stage_url(n) + '#' + layer), (a['title'], None)]),
            ruler(n, layer), LAYER_LABEL[layer], n, esc(STAGES[n]['label']), esc(a['title']), a['learn'], a.get('read', 5),
            ''.join('<span>%s</span>' % esc(x) for x in a.get('tags', [])), draft_note(a),
            tldr, body, sources_block(a), review_line(a), ways(w))
        write(a['url'], layout(a['url'], a['title'], a.get('desc') or ('Bạn sẽ biết: ' + plain(a['learn'])), main, layer, section='chang',
                               kind_label=LAYER_LABEL[layer], draft=is_draft(a)))
        PAGES[a['url']].update({'search': {'k': layer, 'c': '%s · Chặng %d' % (LAYER_LABEL[layer], n), 's': 'Bạn sẽ biết: ' + plain(a['learn']),
                                           'x': ' '.join([a['title'], plain(a['learn']), ' '.join(a.get('keywords', [])), plain(' '.join(a.get('tldr', []))), plain(a['body'])[:4000]])}})


# ---------------------------------------------------------------- hỏi nhanh, từ điển, tìm kiếm
def build_qa():
    groups = []
    for n in range(1, 9):
        qs = [q for q in QUESTIONS if q.get('stage') == n]
        if qs:
            groups.append('<section class="qa-group layer-sec" id="chang-%d"><div class="wrap"><h2>Chặng %d · %s</h2><ul class="qa">%s</ul></div></section>'
                          % (n, n, esc(STAGES[n]['label']), ''.join(qa_item(q) for q in qs)))
    toc = ' · '.join('<a href="#chang-%d">%d · %s</a>' % (n, n, esc(STAGES[n]['label'])) for n in range(1, 9) if any(q.get('stage') == n for q in QUESTIONS))
    main = ('<header class="page-head"><div class="wrap">%s<p class="eyebrow">Hỏi nhanh</p><h1>Bạn đang băn khoăn điều gì?</h1>'
            '<p class="stage-intro">Câu hỏi đời thường, trả lời một hai câu. Muốn hiểu kỹ thì bấm vào bài sâu hơn ở cuối mỗi câu.</p>'
            '<p class="suggest">%s</p></div></header>%s') % (crumbs([('Hỏi nhanh', None)]), toc, ''.join(groups))
    write('/hoi-nhanh/', layout('/hoi-nhanh/', 'Hỏi nhanh', 'Câu hỏi hay gặp khi xây nhà lần đầu, trả lời ngắn gọn: chi phí, giấy phép, hợp đồng, thi công, nhận nhà.', main, 'trang', section='hoi-nhanh'))
    for q in QUESTIONS:
        u = '/hoi-nhanh/#' + q['slug']
        PAGES[u] = {'url': u, 'title': q['q'], 'kind': 'hoi-nhanh', 'anchor': True,
                    'search': {'k': 'hoi-nhanh', 'c': 'Hỏi nhanh · Chặng %d' % q['stage'], 's': plain(q['a'])[:160], 'x': q['q'] + ' ' + plain(q['a']) + ' ' + ' '.join(q.get('keywords', []))}}


def build_glossary():
    terms = sorted(TERMS, key=lambda t: fold(t['term']))
    letters = []
    items = []
    for t in terms:
        L = fold(t['term'])[0].upper()
        anchor = ''
        if L not in letters:
            letters.append(L)
            anchor = ' data-letter="%s"' % L
        see = ''
        if t.get('link'):
            target = t['link']
            title = (ART.get(target.strip('/').split('/')[-1]) or {}).get('title') or t.get('link_label') or 'Đọc thêm'
            see = '<p class="see"><a href="%s">%s →</a></p>' % (target, esc(title))
        ex = '<p class="note">%s</p>' % t['example'] if t.get('example') else ''
        items.append('<div id="%s"%s><dt>%s</dt><dd><p>%s</p>%s%s</dd></div>' % (t['slug'], anchor, esc(t['term']), t['def'], ex, see))
    main = ('<header class="page-head"><div class="wrap">%s<p class="eyebrow">Từ điển xây nhà</p><h1>Nghe thợ nói mà chưa hiểu?</h1>'
            '<p class="stage-intro">Mỗi từ một câu giải thích bằng lời thường. Trong các bài cẩm nang, từ có gạch chân chấm là chạm vào để xem nghĩa.</p></div></header>'
            '<section class="simple"><div class="wrap"><dl class="glossary">%s</dl></div></section>') % (crumbs([('Từ điển', None)]), ''.join(items))
    write('/tu-dien/', layout('/tu-dien/', 'Từ điển xây nhà', 'Giải thích bằng lời thường các thuật ngữ hay gặp khi xây nhà: chỉ giới, diện tích quy đổi, khoán gọn, nghiệm thu, hoàn công…', main, 'trang', section='tu-dien'))
    for t in TERMS:
        u = '/tu-dien/#' + t['slug']
        PAGES[u] = {'url': u, 'title': t['term'], 'kind': 'tu-dien', 'anchor': True,
                    'search': {'k': 'tu-dien', 'c': 'Từ điển', 's': plain(t['def'])[:160], 'x': ' '.join([t['term']] + t.get('aliases', []) + [plain(t['def'])])}}


def build_search_page():
    main = ('<header class="page-head"><div class="wrap">%s<h1>Tìm trong Nhật ký xây nhà</h1>'
            '<form class="searchbox" id="search-form" action="/tim-kiem/" method="get" role="search">'
            '<label class="sr-only" for="q">Từ khoá</label><input id="q" name="q" type="search" placeholder="Ví dụ: xin phép, báo giá, chống thấm…" autocomplete="off">'
            '<button class="btn btn-solid" type="submit">Tìm</button></form>'
            '<p class="note" id="search-status" aria-live="polite"></p></div></header>'
            '<section class="simple"><div class="wrap"><div class="results" id="search-results"></div>'
            '<div class="noresult" id="search-empty" hidden><p>Chưa tìm thấy bài nào khớp. Thử một từ ngắn hơn, hoặc xem các câu hay hỏi:</p>'
            '<p class="suggest">%s</p><p>Hoặc mở <a href="/hoi-nhanh/">Hỏi nhanh</a>, <a href="/tu-dien/">Từ điển</a>, <a href="/ban-do/">bản đồ tám chặng</a>.</p></div>'
            '</div></section>') % (crumbs([('Tìm kiếm', None)]), ' · '.join('<a href="/tim-kiem/?q=%s">%s</a>' % (esc(q), esc(q)) for q in SITE['search_suggestions']))
    head = '<style>.sr-only{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap}</style>\n'
    write('/tim-kiem/', layout('/tim-kiem/', 'Tìm kiếm', 'Tìm trong truyện, công cụ, cẩm nang và từ điển của Nhật ký xây nhà.', main, 'search', section='tim-kiem', extra_head=head))


# ---------------------------------------------------------------- trang chung, địa phương
def build_extra():
    for p in EXTRA:
        url = p['url']
        cr = p.get('crumbs') or [[p['title'], None]]
        tldr = ''
        if p.get('tldr'):
            tldr = '<section class="tldr" aria-label="Tóm tắt 30 giây"><h2>Tóm tắt 30 giây</h2><ul>%s</ul></section>' % ''.join('<li>%s</li>' % x for x in p['tldr'])
        body = link_terms_safe(p['body']) if p.get('glossary', True) else p['body']
        learn = '<p class="learn"><b>Bạn sẽ biết:</b> %s</p>' % p['learn'] if p.get('learn') else ''
        w = [way(x['small'], x['title'], x['href'], x.get('em', ''), x.get('main', False)) for x in p.get('ways', [])]
        main = ('<header class="page-head"><div class="wrap">%s<p class="eyebrow">%s</p><h1>%s</h1>%s%s</div></header>'
                '<article class="article"><div class="wrap">%s<div class="prose">%s</div>%s%s</div></article>%s') % (
            crumbs([(c[0], c[1]) for c in cr]), esc(p.get('eyebrow', '')), esc(p['title']), learn, draft_note(p),
            tldr, body, sources_block(p), review_line(p) if p.get('reviewable') else '', ways(w))
        kind = p.get('kind', 'trang')
        write(url, layout(url, p['title'], p['desc'], main, kind, section=p.get('section', ''), kind_label=p.get('eyebrow', ''), draft=is_draft(p)))
        PAGES[url].update({'search': {'k': 'trang', 'c': p.get('eyebrow', 'Trang'), 's': p['desc'], 'x': p['title'] + ' ' + p['desc'] + ' ' + plain(p['body'])[:3000]}})


def build_404():
    main = ('<section class="page-head"><div class="wrap"><p class="eyebrow">Không tìm thấy trang</p><h1>Trang này không có ở đây</h1>'
            '<p class="stage-intro">Có thể đường dẫn đã đổi khi chúng tôi sắp xếp lại các bài. Xin lỗi vì sự bất tiện.</p>'
            '<form class="searchbox" action="/tim-kiem/" method="get" role="search"><input name="q" type="search" placeholder="Bạn đang tìm gì?" aria-label="Từ khoá">'
            '<button class="btn btn-solid" type="submit">Tìm</button></form>'
            '<p class="hero-more"><a href="/">Về trang đầu</a> · <a href="/ban-do/">Bản đồ tám chặng</a> · <a href="/hoi-nhanh/">Hỏi nhanh</a></p></div></section>')
    write('/404.html', layout('/404.html', 'Không tìm thấy trang', 'Trang bạn tìm không có ở đây.', main, '404'))


# ---------------------------------------------------------------- chỉ mục, sitemap
def build_index_files():
    idx = []
    for url, p in PAGES.items():
        s = p.get('search')
        if not s or (p.get('draft') and HIDE_DRAFTS):
            continue
        idx.append({'t': p['title'], 'u': url, 'k': s['k'], 'c': s.get('c', ''), 's': s.get('s', ''), 'x': fold(s.get('x', ''))[:2500]})
    write('/assets/data/tim-kiem.json', json.dumps(idx, ensure_ascii=False, separators=(',', ':')))
    urls = [u for u, p in PAGES.items() if not p.get('anchor') and not p.get('draft') and p.get('kind') not in ('404', 'search')]
    sm = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for u in sorted(urls):
        sm.append('  <url><loc>%s%s</loc></url>' % (CFG['url'], u))
    sm.append('</urlset>')
    write('/sitemap.xml', '\n'.join(sm) + '\n')
    write('/robots.txt', 'User-agent: *\nAllow: /\nSitemap: %s/sitemap.xml\n' % CFG['url'])


# ---------------------------------------------------------------- kiểm tra
def check():
    errors = []
    ids_cache = {}
    def ids_of(rel):
        if rel not in ids_cache:
            with open(os.path.join(ROOT, rel), encoding='utf-8') as f:
                ids_cache[rel] = set(re.findall(r'\sid="([^"]+)"', f.read()))
        return ids_cache[rel]
    for rel in GENERATED:
        if not rel.endswith('.html'):
            continue
        with open(os.path.join(ROOT, rel), encoding='utf-8') as f:
            t = f.read()
        for tag in ('<title>', 'name="description"', 'rel="canonical"'):
            if tag not in t:
                errors.append('%s: thiếu %s' % (rel, tag))
        for href in re.findall(r'(?:href|src)="(/[^"]*)"', t):
            if href.startswith('//'):
                continue
            pth, _, frag = href.partition('#')
            pth = pth.split('?')[0]
            target = pth.lstrip('/')
            if target == '' or target.endswith('/'):
                target += 'index.html'
            if not os.path.exists(os.path.join(ROOT, target)):
                errors.append('%s: liên kết gãy %s' % (rel, href))
            elif frag and target.endswith('.html') and frag not in ids_of(target):
                errors.append('%s: không có mục #%s trong %s' % (rel, frag, pth or '/'))
        for frag in re.findall(r'href="#([^"]+)"', t):
            if frag not in ids_of(rel):
                errors.append('%s: không có mục #%s trong chính trang' % (rel, frag))
        ids = re.findall(r'\sid="([^"]+)"', t)
        dup = sorted(set(i for i in ids if ids.count(i) > 1))
        if dup:
            errors.append('%s: id bị trùng %s' % (rel, ', '.join(dup[:5])))
    return errors


def main():
    build_qa()
    build_glossary()
    build_home()
    build_stages()
    build_map()
    build_stories()
    build_tools()
    build_articles()
    build_search_page()
    build_extra()
    build_404()
    build_index_files()
    errors = check()
    drafts = [a['url'] for a in ARTICLES if is_draft(a)] + [p['url'] for p in EXTRA if is_draft(p)]
    print('Đã dựng %d tệp (%d trang nội dung).' % (len(GENERATED), len([u for u, p in PAGES.items() if not p.get('anchor')])))
    if drafts:
        print('%d bài còn là bản nháp (status "cho-duyet")%s:' % (len(drafts), ', đã bỏ ra khỏi website' if HIDE_DRAFTS else ', vẫn hiện kèm ghi chú "Bản nháp"'))
        for d in drafts:
            print('  -', d)
    for w in WARN:
        print('Cảnh báo:', w)
    if errors:
        print('\n%d lỗi:' % len(errors))
        for e in errors:
            print('  -', e)
        sys.exit(1)
    print('Kiểm tra liên kết: không có lỗi.')


if __name__ == '__main__':
    main()
