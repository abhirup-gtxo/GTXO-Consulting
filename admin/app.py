import os
import sys
import json
import uuid
import base64
import shutil
from datetime import datetime
from functools import wraps
from pathlib import Path

import requests
from flask import (Flask, render_template, request, redirect, url_for,
                   session, jsonify, send_from_directory, abort, flash)
from bs4 import BeautifulSoup, NavigableString

sys.path.insert(0, str(Path(__file__).parent))
from content_maps import PAGES

app = Flask(__name__, template_folder='templates', static_folder='static', static_url_path='/admin/static')
app.secret_key = os.environ.get('SECRET_KEY', 'gtxo-admin-2026-secret')

SITE_ROOT  = Path(__file__).parent.parent
ADMIN_ROOT = Path(__file__).parent
DATA_DIR   = ADMIN_ROOT / 'data'
DATA_DIR.mkdir(exist_ok=True)

ADMIN_USER = os.environ.get('ADMIN_USER', 'admin')
ADMIN_PASS = os.environ.get('ADMIN_PASSWORD', 'gtxo2026')

# GitHub API — set these env vars on Railway
GITHUB_TOKEN  = os.environ.get('GITHUB_TOKEN', '')
GITHUB_REPO   = os.environ.get('GITHUB_REPO', 'abhirup-gtxo/GTXO-Consulting')
GITHUB_BRANCH = os.environ.get('GITHUB_BRANCH', 'main')
USE_GITHUB    = bool(GITHUB_TOKEN)

CMS_TYPES = {
    'blogs':        {'label': 'Blogs',        'cover_label': 'BLOG',        'kind_default': 'Essay'},
    'case-studies': {'label': 'Case Studies', 'cover_label': 'CASE STUDY',  'kind_default': 'B2B SaaS'},
    'guides':       {'label': 'Guides',       'cover_label': 'GUIDE',       'kind_default': 'Guide'},
}
GRAD_OPTIONS = ['grad-a', 'grad-b', 'grad-c', 'grad-d']

# ── GitHub API helpers ────────────────────────────────────────────────────────

def _gh_headers():
    return {
        'Authorization': f'token {GITHUB_TOKEN}',
        'Accept': 'application/vnd.github.v3+json',
    }

def _gh_get(repo_path):
    """Return (content_str, sha) or (None, None)."""
    url = f'https://api.github.com/repos/{GITHUB_REPO}/contents/{repo_path}'
    r = requests.get(url, headers=_gh_headers(), params={'ref': GITHUB_BRANCH})
    if r.status_code == 200:
        data = r.json()
        content = base64.b64decode(data['content']).decode('utf-8')
        return content, data['sha']
    return None, None

def _gh_put(repo_path, content_str, commit_msg, sha=None):
    """Create or update a file in the GitHub repo."""
    url = f'https://api.github.com/repos/{GITHUB_REPO}/contents/{repo_path}'
    payload = {
        'message': commit_msg,
        'content': base64.b64encode(content_str.encode('utf-8')).decode('ascii'),
        'branch':  GITHUB_BRANCH,
    }
    if sha:
        payload['sha'] = sha
    r = requests.put(url, headers=_gh_headers(), json=payload)
    return r.status_code in (200, 201)

# ── Generic read/write (local or GitHub) ─────────────────────────────────────

def _read_file(repo_path):
    """Read a file — from GitHub if token set, otherwise local."""
    if USE_GITHUB:
        content, _ = _gh_get(repo_path)
        return content
    full = SITE_ROOT / repo_path
    if not full.exists():
        return None
    return full.read_text(encoding='utf-8')

def _write_file(repo_path, content_str, commit_msg='Update'):
    """Write a file — to GitHub if token set, otherwise local."""
    if USE_GITHUB:
        _, sha = _gh_get(repo_path)
        return _gh_put(repo_path, content_str, commit_msg, sha)
    full = SITE_ROOT / repo_path
    full.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(full, full.with_suffix('.bak')) if full.exists() else None
    full.write_text(content_str, encoding='utf-8')
    return True

# ── CMS helpers ───────────────────────────────────────────────────────────────

def _cms_repo_path(ct):
    return f'admin/data/{ct}.json'

def load_cms(ct):
    if USE_GITHUB:
        content, _ = _gh_get(_cms_repo_path(ct))
        return json.loads(content) if content else []
    p = DATA_DIR / f'{ct}.json'
    if not p.exists():
        return []
    with open(p) as f:
        return json.load(f)

def save_cms(ct, data):
    content = json.dumps(data, indent=2, default=str)
    if USE_GITHUB:
        _, sha = _gh_get(_cms_repo_path(ct))
        _gh_put(_cms_repo_path(ct), content, f'CMS: update {ct}', sha)
    else:
        with open(DATA_DIR / f'{ct}.json', 'w') as f:
            f.write(content)

# ── Auth ──────────────────────────────────────────────────────────────────────

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

@app.context_processor
def inject_nav():
    pages_list = [{'key': k, 'label': v['label'], 'file': v['file']} for k, v in PAGES.items()]
    return dict(pages_list=pages_list, cms_types=CMS_TYPES)

# ── Page-content helpers ──────────────────────────────────────────────────────

def read_page(page_key):
    page = PAGES[page_key]
    html = _read_file(page['file'])
    if not html:
        return None, {}
    soup = BeautifulSoup(html, 'lxml')
    values = {}
    for section in page['sections']:
        for field in section['fields']:
            el = soup.select_one(field['selector'])
            if el is None:
                values[field['id']] = ''
                continue
            if field['type'] == 'text':
                values[field['id']] = el.get_text(strip=True)
            elif field['type'] == 'html':
                values[field['id']] = el.decode_contents()
            elif field['type'] == 'href':
                values[field['id']] = el.get('href', '')
            else:
                values[field['id']] = el.get_text(strip=True)
    return soup, values

def write_page(page_key, form_data):
    page = PAGES[page_key]
    html = _read_file(page['file'])
    if not html:
        return False, 'File not found'

    soup = BeautifulSoup(html, 'lxml')
    for section in page['sections']:
        for field in section['fields']:
            fid = field['id']
            if fid not in form_data:
                continue
            val = form_data[fid]
            el = soup.select_one(field['selector'])
            if el is None:
                continue
            if field['type'] == 'text':
                replaced = False
                for child in list(el.children):
                    if isinstance(child, NavigableString):
                        child.replace_with(NavigableString(val))
                        replaced = True
                        break
                if not replaced:
                    el.string = val
            elif field['type'] == 'html':
                new_inner = BeautifulSoup(f'<div>{val}</div>', 'html.parser').find('div')
                el.clear()
                for child in list(new_inner.children):
                    el.append(child)
            elif field['type'] == 'href':
                el['href'] = val

    ok = _write_file(page['file'], str(soup), f'Page edit: {page["label"]}')
    return ok, 'Saved' if ok else 'Save failed'

# ── Auth routes ───────────────────────────────────────────────────────────────

@app.route('/admin/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        if (request.form.get('username') == ADMIN_USER and
                request.form.get('password') == ADMIN_PASS):
            session['logged_in'] = True
            return redirect(url_for('dashboard'))
        error = 'Invalid credentials'
    return render_template('login.html', error=error)

@app.route('/admin/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ── Dashboard ─────────────────────────────────────────────────────────────────

@app.route('/admin/')
@app.route('/admin')
@login_required
def dashboard():
    counts = {ct: len(load_cms(ct)) for ct in CMS_TYPES}
    return render_template('dashboard.html', cms_types=CMS_TYPES, counts=counts)

# ── Page editor ───────────────────────────────────────────────────────────────

@app.route('/admin/page/<page_key>', methods=['GET', 'POST'])
@login_required
def page_editor(page_key):
    if page_key not in PAGES:
        abort(404)
    if request.method == 'POST':
        ok, msg = write_page(page_key, request.form)
        flash(msg, 'success' if ok else 'error')
        return redirect(url_for('page_editor', page_key=page_key))
    _, values = read_page(page_key)
    return render_template('page_editor.html',
                           page_key=page_key,
                           page_meta=PAGES[page_key],
                           values=values)

# ── CMS list ──────────────────────────────────────────────────────────────────

@app.route('/admin/cms/<ct>')
@login_required
def cms_list(ct):
    if ct not in CMS_TYPES:
        abort(404)
    items = load_cms(ct)
    items.sort(key=lambda x: x.get('updated_at', ''), reverse=True)
    return render_template('cms_list.html', ct=ct, meta=CMS_TYPES[ct], items=items)

# ── CMS new ───────────────────────────────────────────────────────────────────

@app.route('/admin/cms/<ct>/new', methods=['GET', 'POST'])
@login_required
def cms_new(ct):
    if ct not in CMS_TYPES:
        abort(404)
    if request.method == 'POST':
        items = load_cms(ct)
        now = datetime.utcnow().isoformat()
        item = {
            'id':          str(uuid.uuid4()),
            'title':       request.form.get('title', '').strip(),
            'slug':        _slugify(request.form.get('title', '')),
            'cover_glyph': request.form.get('cover_glyph', '').strip(),
            'cover_grad':  request.form.get('cover_grad', 'grad-a'),
            'kind':        request.form.get('kind', CMS_TYPES[ct]['kind_default']).strip(),
            'tags':        [t.strip() for t in request.form.get('tags', '').split(',') if t.strip()],
            'description': request.form.get('description', '').strip(),
            'content':     request.form.get('content', ''),
            'published':   request.form.get('published') == 'on',
            'created_at':  now,
            'updated_at':  now,
        }
        items.append(item)
        save_cms(ct, items)
        _rebuild_resource_page(ct)
        flash('Created successfully', 'success')
        return redirect(url_for('cms_list', ct=ct))
    return render_template('cms_edit.html', ct=ct, meta=CMS_TYPES[ct],
                           item=None, grad_options=GRAD_OPTIONS)

# ── CMS edit ──────────────────────────────────────────────────────────────────

@app.route('/admin/cms/<ct>/<item_id>/edit', methods=['GET', 'POST'])
@login_required
def cms_edit(ct, item_id):
    if ct not in CMS_TYPES:
        abort(404)
    items = load_cms(ct)
    item = next((i for i in items if i['id'] == item_id), None)
    if item is None:
        abort(404)
    if request.method == 'POST':
        item['title']       = request.form.get('title', '').strip()
        item['cover_glyph'] = request.form.get('cover_glyph', '').strip()
        item['cover_grad']  = request.form.get('cover_grad', 'grad-a')
        item['kind']        = request.form.get('kind', '').strip()
        item['tags']        = [t.strip() for t in request.form.get('tags', '').split(',') if t.strip()]
        item['description'] = request.form.get('description', '').strip()
        item['content']     = request.form.get('content', '')
        item['published']   = request.form.get('published') == 'on'
        item['updated_at']  = datetime.utcnow().isoformat()
        save_cms(ct, items)
        _rebuild_resource_page(ct)
        flash('Saved successfully', 'success')
        return redirect(url_for('cms_list', ct=ct))
    return render_template('cms_edit.html', ct=ct, meta=CMS_TYPES[ct],
                           item=item, grad_options=GRAD_OPTIONS)

# ── CMS delete / toggle ───────────────────────────────────────────────────────

@app.route('/admin/cms/<ct>/<item_id>/delete', methods=['POST'])
@login_required
def cms_delete(ct, item_id):
    if ct not in CMS_TYPES:
        abort(404)
    items = [i for i in load_cms(ct) if i['id'] != item_id]
    save_cms(ct, items)
    _rebuild_resource_page(ct)
    flash('Deleted', 'success')
    return redirect(url_for('cms_list', ct=ct))

@app.route('/admin/cms/<ct>/<item_id>/toggle', methods=['POST'])
@login_required
def cms_toggle(ct, item_id):
    items = load_cms(ct)
    for i in items:
        if i['id'] == item_id:
            i['published'] = not i.get('published', False)
            i['updated_at'] = datetime.utcnow().isoformat()
    save_cms(ct, items)
    _rebuild_resource_page(ct)
    return redirect(url_for('cms_list', ct=ct))

# ── Public JSON API ───────────────────────────────────────────────────────────

@app.route('/api/cms/<ct>')
def api_cms(ct):
    if ct not in CMS_TYPES:
        abort(404)
    items = [i for i in load_cms(ct) if i.get('published')]
    items.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    return jsonify(items)

@app.route('/api/cms/<ct>/<item_id>')
def api_article(ct, item_id):
    if ct not in CMS_TYPES:
        abort(404)
    items = load_cms(ct)
    item = next((i for i in items if i['id'] == item_id and i.get('published')), None)
    if not item:
        abort(404)
    return jsonify(item)

# ── Static site passthrough (local only) ─────────────────────────────────────

if not USE_GITHUB:
    @app.route('/uploads/<path:filename>')
    def serve_upload(filename):
        return send_from_directory(str(SITE_ROOT / 'uploads'), filename)

    @app.route('/', defaults={'path': 'index.html'})
    @app.route('/<path:path>')
    def serve_site(path):
        if path.startswith('admin') or path.startswith('api'):
            abort(404)
        full = SITE_ROOT / path
        if full.is_dir():
            full = full / 'index.html'
        if full.exists():
            return send_from_directory(str(full.parent), full.name)
        abort(404)

# ── Article + resource page generators ───────────────────────────────────────

ARTICLE_TEMPLATE = """\
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>{title} · Grow10x</title>
  <link rel="stylesheet" href="../../assets/site.css">
</head>
<body data-page="resources" data-depth="2">
  <header id="site-nav"></header>
  <main>
    <section class="hero">
      <div class="container inner" style="max-width:760px;">
        <div class="crumbs">
          <a href="/">Home</a> <span>/</span>
          <a href="/resources">Resources</a> <span>/</span>
          <a href="/resources/{ct}">{ct_label}</a> <span>/</span>
          <span>{title}</span>
        </div>
        <p class="eyebrow"><span class="dash"></span> {cover_label}</p>
        <h1 class="display">{title}</h1>
        <p class="lead">{description}</p>
        <div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:16px;">
          <span class="eyebrow pill">{kind}</span>
          {tag_pills}
        </div>
      </div>
    </section>
    <section class="section">
      <div class="container" style="max-width:760px;">
        <div class="article-body">
          {content}
        </div>
        <div style="margin-top:64px;padding-top:40px;border-top:1px solid var(--border);">
          <a href="/resources/{ct}" class="btn btn-ghost btn-sm">← Back to {ct_label}</a>
        </div>
      </div>
    </section>
  </main>
  <footer id="site-footer"></footer>
  <script src="../../assets/shell.js"></script>
  <style>
    .article-body h1,.article-body h2,.article-body h3{{margin-top:2em;margin-bottom:.5em;font-family:var(--font-display);}}
    .article-body p{{margin-bottom:1.2em;line-height:1.75;}}
    .article-body ul,.article-body ol{{margin-bottom:1.2em;padding-left:1.5em;}}
    .article-body blockquote{{border-left:3px solid var(--gtxo-blue-500);padding-left:20px;color:var(--fg-secondary);font-style:italic;}}
    .article-body a{{color:var(--gtxo-blue-500);text-decoration:underline;}}
  </style>
</body>
</html>"""

def _generate_article_pages(ct):
    items = load_cms(ct)
    meta  = CMS_TYPES[ct]
    published_ids = {i['id'] for i in items if i.get('published')}

    # Delete stale articles from GitHub / local
    if USE_GITHUB:
        url = f'https://api.github.com/repos/{GITHUB_REPO}/contents/resources/{ct}'
        r = requests.get(url, headers=_gh_headers(), params={'ref': GITHUB_BRANCH})
        if r.status_code == 200:
            for f in r.json():
                stem = Path(f['name']).stem
                if stem not in published_ids:
                    requests.delete(
                        f['url'], headers=_gh_headers(),
                        json={'message': f'CMS: remove {ct}/{f["name"]}',
                              'sha': f['sha'], 'branch': GITHUB_BRANCH}
                    )
    else:
        out_dir = SITE_ROOT / 'resources' / ct
        out_dir.mkdir(exist_ok=True)
        for p in out_dir.glob('*.html'):
            if p.stem not in published_ids:
                p.unlink(missing_ok=True)

    for item in items:
        if not item.get('published'):
            continue
        tag_pills = ''.join(
            f'<span class="eyebrow pill">{t}</span>'
            for t in item.get('tags', [])
        )
        html = ARTICLE_TEMPLATE.format(
            title=item['title'],
            description=item.get('description', ''),
            content=item.get('content', ''),
            cover_label=meta['cover_label'],
            ct=ct,
            ct_label=meta['label'],
            kind=item.get('kind', ''),
            tag_pills=tag_pills,
        )
        repo_path = f'resources/{ct}/{item["id"]}.html'
        _write_file(repo_path, html, f'CMS: publish {ct} article')

def _rebuild_resource_page(ct):
    _generate_article_pages(ct)

    page_map = {
        'blogs':        'resources/blogs.html',
        'case-studies': 'resources/case-studies.html',
        'guides':       'resources/guides.html',
    }
    repo_path = page_map[ct]
    html = _read_file(repo_path)
    if not html:
        return

    items = [i for i in load_cms(ct) if i.get('published')]
    items.sort(key=lambda x: x.get('created_at', ''), reverse=True)

    cover_label = CMS_TYPES[ct]['cover_label']
    if items:
        cards_html = ''
        for item in items:
            tags_html = ''.join(
                f'<span>{t}</span><span class="dot"></span>'
                for t in item.get('tags', [])
            ).rstrip('<span class="dot"></span>')
            item_url = f'{ct}/{item["id"]}.html'
            cards_html += f'''
    <a class="res-card" href="{item_url}" data-cms-id="{item["id"]}">
      <div class="cover {item.get("cover_grad","grad-a")}">
        <span class="cover-label">{cover_label}</span>
        <span class="cover-glyph">{item.get("cover_glyph","")}</span>
      </div>
      <div class="body">
        <span class="kind">{item.get("kind","")}</span>
        <h3 class="ttl">{item["title"]}</h3>
        <p class="desc">{item.get("description","")}</p>
        <div class="meta">{tags_html}</div>
      </div>
    </a>'''
    else:
        cards_html = '<p class="lead" style="color:var(--fg-secondary);padding:40px 0;">No published entries yet.</p>'

    soup = BeautifulSoup(html, 'lxml')
    grid = soup.select_one('.res-grid')
    if grid:
        banner = soup.select_one('.status-banner')
        if banner:
            banner.decompose()
        grid.clear()
        frag = BeautifulSoup(cards_html, 'html.parser')
        for child in list(frag.children):
            grid.append(child)

    _write_file(repo_path, str(soup), f'CMS: rebuild {ct} listing')

# ── Testimonials data helpers ─────────────────────────────────────────────────

TESTIMONIALS_PATH = 'admin/data/testimonials.json'

def load_testimonials():
    if USE_GITHUB:
        content, _ = _gh_get(TESTIMONIALS_PATH)
        return json.loads(content) if content else []
    p = DATA_DIR / 'testimonials.json'
    if not p.exists():
        return []
    with open(p) as f:
        return json.load(f)

def save_testimonials(data):
    content = json.dumps(data, indent=2, ensure_ascii=False)
    if USE_GITHUB:
        _, sha = _gh_get(TESTIMONIALS_PATH)
        _gh_put(TESTIMONIALS_PATH, content, 'Testimonials: update', sha)
    else:
        with open(DATA_DIR / 'testimonials.json', 'w') as f:
            f.write(content)

def _initials(name):
    parts = name.split()
    return ''.join(p[0].upper() for p in parts if p)[:2]

def _t_card_html(item):
    from html import escape
    import re
    name   = escape(item.get('name', ''))
    desg   = escape(item.get('designation', ''))
    co     = escape(item.get('company', ''))
    tid    = item.get('id', '')
    initls = _initials(item.get('name', ''))

    # Build quote: each line → display:block span; blank lines add a gap class
    raw = item.get('testimonial', '').replace('\r\n', '\n').strip()
    blocks = re.split(r'\n{2,}', raw)
    spans = []
    for b_idx, block in enumerate(blocks):
        lines = [escape(l.strip()) for l in block.split('\n') if l.strip()]
        last_block = (b_idx == len(blocks) - 1)
        for l_idx, line in enumerate(lines):
            last_in_block = (l_idx == len(lines) - 1)
            gap = ' tl-gap' if last_in_block and not last_block else ''
            spans.append(f'<span class="tl{gap}">{line}</span>')
    quote_html = '&#x201C;' + ''.join(spans) + '&#x201D;'

    return (
        f'\n    <div class="t-card" data-tid="{tid}">'
        f'\n      <div class="t-head">'
        f'\n        <div class="t-avatar">{initls}</div>'
        f'\n        <div>'
        f'\n          <div class="t-name">{name}</div>'
        f'\n          <div class="t-role">{desg} · {co}</div>'
        f'\n        </div>'
        f'\n      </div>'
        f'\n      <p class="t-quote">{quote_html}</p>'
        f'\n    </div>'
    )

# ── Logo helpers ─────────────────────────────────────────────────────────────

LOGOS_PATH      = 'admin/data/logos.json'
LOGOS_ASSET_DIR = 'assets/clients'

def load_logos():
    if USE_GITHUB:
        content, _ = _gh_get(LOGOS_PATH)
        return json.loads(content) if content else []
    p = DATA_DIR / 'logos.json'
    return json.loads(p.read_text()) if p.exists() else []

def save_logos(data):
    content = json.dumps(data, indent=2, ensure_ascii=False)
    if USE_GITHUB:
        _, sha = _gh_get(LOGOS_PATH)
        _gh_put(LOGOS_PATH, content, 'Logos: update manifest', sha)
    else:
        (DATA_DIR / 'logos.json').write_text(content)

def _write_binary_file(repo_path, file_bytes, commit_msg='Upload'):
    if USE_GITHUB:
        _, sha = _gh_get(repo_path)
        url = f'https://api.github.com/repos/{GITHUB_REPO}/contents/{repo_path}'
        payload = {
            'message': commit_msg,
            'content': base64.b64encode(file_bytes).decode('ascii'),
            'branch':  GITHUB_BRANCH,
        }
        if sha:
            payload['sha'] = sha
        r = requests.put(url, headers=_gh_headers(), json=payload)
        return r.status_code in (200, 201)
    full = SITE_ROOT / repo_path
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_bytes(file_bytes)
    return True

def _delete_file(repo_path, commit_msg='Delete'):
    if USE_GITHUB:
        _, sha = _gh_get(repo_path)
        if sha:
            url = f'https://api.github.com/repos/{GITHUB_REPO}/contents/{repo_path}'
            requests.delete(url, headers=_gh_headers(),
                            json={'message': commit_msg, 'sha': sha, 'branch': GITHUB_BRANCH})
    else:
        full = SITE_ROOT / repo_path
        if full.exists():
            full.unlink()

def _rebuild_logo_wall():
    from html import escape as _esc
    logos = [l for l in load_logos() if l.get('active')]
    cells = ''.join(
        f'\n<div class="logo-cell"><img src="assets/clients/{l["filename"]}" alt="{_esc(l.get("alt",""))}"></div>'
        for l in logos
    ) + '\n'
    html = _read_file('clients.html')
    if not html:
        return
    soup = BeautifulSoup(html, 'lxml')
    wall = soup.select_one('.logo-wall')
    if not wall:
        return
    wall.clear()
    frag = BeautifulSoup(cells, 'html.parser')
    for child in list(frag.children):
        wall.append(child)
    _write_file('clients.html', str(soup), 'Logos: rebuild logo wall')

def _logo_preview_url(filename):
    if USE_GITHUB:
        return f'https://raw.githubusercontent.com/{GITHUB_REPO}/main/assets/clients/{filename}'
    return f'/assets/clients/{filename}'

# ── Logo routes ───────────────────────────────────────────────────────────────

@app.route('/admin/logos')
@login_required
def logos_list():
    items = load_logos()
    for item in items:
        item['preview_url'] = _logo_preview_url(item['filename'])
    return render_template('logos.html', items=items)

@app.route('/admin/logos/upload', methods=['POST'])
@login_required
def logo_upload():
    f = request.files.get('logo_file')
    alt = request.form.get('alt', '').strip()
    if not f or not alt:
        flash('File and company name are required', 'error')
        return redirect(url_for('logos_list'))

    ext = Path(f.filename).suffix.lower() or '.png'
    slug = _slugify(alt)
    filename = f'{slug}{ext}'
    repo_path = f'{LOGOS_ASSET_DIR}/{filename}'

    ok = _write_binary_file(repo_path, f.read(), f'Logos: upload {filename}')
    if not ok:
        flash('Upload failed', 'error')
        return redirect(url_for('logos_list'))

    logos = load_logos()
    # Replace existing entry with same filename if present
    logos = [l for l in logos if l['filename'] != filename]
    logos.append({
        'id':         str(uuid.uuid4()),
        'filename':   filename,
        'alt':        alt,
        'active':     True,
        'created_at': datetime.utcnow().isoformat(),
    })
    save_logos(logos)
    _rebuild_logo_wall()
    flash(f'{alt} uploaded and published', 'success')
    return redirect(url_for('logos_list'))

@app.route('/admin/logos/<item_id>/delete', methods=['POST'])
@login_required
def logo_delete(item_id):
    logos = load_logos()
    item = next((l for l in logos if l['id'] == item_id), None)
    if item:
        _delete_file(f'{LOGOS_ASSET_DIR}/{item["filename"]}', f'Logos: delete {item["filename"]}')
        logos = [l for l in logos if l['id'] != item_id]
        save_logos(logos)
        _rebuild_logo_wall()
        flash(f'{item["alt"]} deleted', 'success')
    return redirect(url_for('logos_list'))

@app.route('/admin/logos/<item_id>/toggle', methods=['POST'])
@login_required
def logo_toggle(item_id):
    logos = load_logos()
    for l in logos:
        if l['id'] == item_id:
            l['active'] = not l.get('active', True)
    save_logos(logos)
    _rebuild_logo_wall()
    return redirect(url_for('logos_list'))

TESTIMONIAL_PAGES = {
    'index.html':                         'first3',
    'clients.html':                       'all',
    'solutions/paid-marketing.html':      'first3',
    'solutions/demand-gen.html':          'first3',
    'solutions/gtm-strategy.html':        'first3',
    'solutions/content-strategy.html':    'first3',
    'solutions/ai-led-seo.html':          'first3',
    'solutions/ai-solutions.html':        'first3',
}

def _rebuild_testimonials():
    items = [i for i in load_testimonials() if i.get('active')]
    for repo_path, mode in TESTIMONIAL_PAGES.items():
        subset = items if mode == 'all' else items[:3]
        _inject_tgrid(repo_path, subset)

def _inject_tgrid(repo_path, items):
    html = _read_file(repo_path)
    if not html:
        return
    soup = BeautifulSoup(html, 'lxml')
    grid = soup.select_one('.tgrid')
    if not grid:
        return
    grid.clear()
    if items:
        cards_html = ''.join(_t_card_html(i) for i in items) + '\n    '
        frag = BeautifulSoup(cards_html, 'html.parser')
        for child in list(frag.children):
            grid.append(child)
    else:
        grid.append(BeautifulSoup('<p class="lead" style="color:var(--fg-secondary);padding:40px 0;">No testimonials yet.</p>', 'html.parser'))
    _write_file(repo_path, str(soup), f'Testimonials: rebuild {repo_path}')

# ── Testimonial routes ────────────────────────────────────────────────────────

@app.route('/admin/testimonials')
@login_required
def testimonials_list():
    items = load_testimonials()
    return render_template('testimonials.html', items=items)

@app.route('/admin/testimonials/new', methods=['GET', 'POST'])
@login_required
def testimonial_new():
    if request.method == 'POST':
        items = load_testimonials()
        now = datetime.utcnow().isoformat()
        item = {
            'id':          str(uuid.uuid4()),
            'name':        request.form.get('name', '').strip(),
            'designation': request.form.get('designation', '').strip(),
            'company':     request.form.get('company', '').strip(),
            'testimonial': request.form.get('testimonial', '').strip(),
            'active':      request.form.get('active') == 'on',
            'created_at':  now,
            'updated_at':  now,
        }
        items.append(item)
        save_testimonials(items)
        _rebuild_testimonials()
        flash('Testimonial added and site updated', 'success')
        return redirect(url_for('testimonials_list'))
    return render_template('testimonial_edit.html', item=None)

@app.route('/admin/testimonials/<item_id>/edit', methods=['GET', 'POST'])
@login_required
def testimonial_edit(item_id):
    items = load_testimonials()
    item = next((i for i in items if i['id'] == item_id), None)
    if item is None:
        abort(404)
    if request.method == 'POST':
        item['name']        = request.form.get('name', '').strip()
        item['designation'] = request.form.get('designation', '').strip()
        item['company']     = request.form.get('company', '').strip()
        item['testimonial'] = request.form.get('testimonial', '').strip()
        item['active']      = request.form.get('active') == 'on'
        item['updated_at']  = datetime.utcnow().isoformat()
        save_testimonials(items)
        _rebuild_testimonials()
        flash('Saved and site updated', 'success')
        return redirect(url_for('testimonials_list'))
    return render_template('testimonial_edit.html', item=item)

@app.route('/admin/testimonials/<item_id>/delete', methods=['POST'])
@login_required
def testimonial_delete(item_id):
    items = [i for i in load_testimonials() if i['id'] != item_id]
    save_testimonials(items)
    _rebuild_testimonials()
    flash('Deleted and site updated', 'success')
    return redirect(url_for('testimonials_list'))

@app.route('/admin/testimonials/<item_id>/toggle', methods=['POST'])
@login_required
def testimonial_toggle(item_id):
    items = load_testimonials()
    for i in items:
        if i['id'] == item_id:
            i['active'] = not i.get('active', True)
            i['updated_at'] = datetime.utcnow().isoformat()
    save_testimonials(items)
    _rebuild_testimonials()
    return redirect(url_for('testimonials_list'))

# ── Helpers ───────────────────────────────────────────────────────────────────

def _slugify(text):
    import re
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_-]+', '-', text)
    return text[:80]

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 3001))
    print(f'GTXO Admin → http://localhost:{port}/admin/')
    app.run(host='0.0.0.0', port=port, debug=not USE_GITHUB)
