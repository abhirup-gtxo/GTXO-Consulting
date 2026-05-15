import os
import sys
import json
import uuid
import shutil
import mimetypes
from datetime import datetime
from functools import wraps
from pathlib import Path

from flask import (Flask, render_template, request, redirect, url_for,
                   session, jsonify, send_from_directory, abort, flash)
from bs4 import BeautifulSoup, NavigableString

sys.path.insert(0, str(Path(__file__).parent))
from content_maps import PAGES

app = Flask(__name__, template_folder='templates', static_folder='static')
app.secret_key = 'gtxo-admin-2026-secret'

@app.context_processor
def inject_nav():
    pages_list = [{'key': k, 'label': v['label'], 'file': v['file']} for k, v in PAGES.items()]
    return dict(pages_list=pages_list, cms_types=CMS_TYPES)

SITE_ROOT  = Path(__file__).parent.parent
ADMIN_ROOT = Path(__file__).parent
DATA_DIR   = ADMIN_ROOT / 'data'
DATA_DIR.mkdir(exist_ok=True)

ADMIN_USER = 'admin'
ADMIN_PASS = 'gtxo2026'

CMS_TYPES = {
    'blogs':        {'label': 'Blogs',        'cover_label': 'BLOG',        'kind_default': 'Essay'},
    'case-studies': {'label': 'Case Studies', 'cover_label': 'CASE STUDY',  'kind_default': 'B2B SaaS'},
    'guides':       {'label': 'Guides',       'cover_label': 'GUIDE',       'kind_default': 'Guide'},
}

GRAD_OPTIONS = ['grad-a', 'grad-b', 'grad-c', 'grad-d']

# ── Auth ─────────────────────────────────────────────────────────────────────

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

# ── CMS helpers ──────────────────────────────────────────────────────────────

def cms_path(ct):
    return DATA_DIR / f'{ct}.json'

def load_cms(ct):
    p = cms_path(ct)
    if not p.exists():
        return []
    with open(p) as f:
        return json.load(f)

def save_cms(ct, data):
    with open(cms_path(ct), 'w') as f:
        json.dump(data, f, indent=2, default=str)

# ── Page-content helpers ─────────────────────────────────────────────────────

def read_page(page_key):
    page = PAGES[page_key]
    html_path = SITE_ROOT / page['file']
    if not html_path.exists():
        return None, {}
    with open(html_path, encoding='utf-8') as f:
        soup = BeautifulSoup(f.read(), 'lxml')
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
    html_path = SITE_ROOT / page['file']
    if not html_path.exists():
        return False, 'File not found'

    with open(html_path, encoding='utf-8') as f:
        soup = BeautifulSoup(f.read(), 'lxml')

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
                # Replace first text node, keeping child elements (e.g. <span class="arr">)
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

    # backup
    backup = html_path.with_suffix('.bak')
    shutil.copy2(html_path, backup)

    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(str(soup))
    return True, 'Saved'

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
    pages_list = [{'key': k, 'label': v['label'], 'file': v['file']} for k, v in PAGES.items()]
    return render_template('dashboard.html', pages=pages_list, cms_types=CMS_TYPES, counts=counts)

# ── Page editor ───────────────────────────────────────────────────────────────

@app.route('/admin/page/<page_key>', methods=['GET', 'POST'])
@login_required
def page_editor(page_key):
    if page_key not in PAGES:
        abort(404)
    page_meta = PAGES[page_key]

    if request.method == 'POST':
        ok, msg = write_page(page_key, request.form)
        flash(msg, 'success' if ok else 'error')
        return redirect(url_for('page_editor', page_key=page_key))

    _, values = read_page(page_key)
    return render_template('page_editor.html',
                           page_key=page_key,
                           page_meta=page_meta,
                           values=values,
                           cms_types=CMS_TYPES)

# ── CMS list ──────────────────────────────────────────────────────────────────

@app.route('/admin/cms/<ct>')
@login_required
def cms_list(ct):
    if ct not in CMS_TYPES:
        abort(404)
    items = load_cms(ct)
    items.sort(key=lambda x: x.get('updated_at', ''), reverse=True)
    return render_template('cms_list.html', ct=ct, meta=CMS_TYPES[ct],
                           items=items, cms_types=CMS_TYPES)

# ── CMS create / edit ─────────────────────────────────────────────────────────

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
                           item=None, grad_options=GRAD_OPTIONS, cms_types=CMS_TYPES)

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
                           item=item, grad_options=GRAD_OPTIONS, cms_types=CMS_TYPES)

@app.route('/admin/cms/<ct>/<item_id>/delete', methods=['POST'])
@login_required
def cms_delete(ct, item_id):
    if ct not in CMS_TYPES:
        abort(404)
    items = load_cms(ct)
    items = [i for i in items if i['id'] != item_id]
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

# ── Public API (used by resource pages) ───────────────────────────────────────

@app.route('/api/cms/<ct>')
def api_cms(ct):
    if ct not in CMS_TYPES:
        abort(404)
    items = load_cms(ct)
    published = [i for i in items if i.get('published')]
    published.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    return jsonify(published)

# ── Image upload ──────────────────────────────────────────────────────────────

@app.route('/admin/upload', methods=['POST'])
@login_required
def upload():
    f = request.files.get('file')
    if not f:
        return jsonify({'error': 'no file'}), 400
    ext = Path(f.filename).suffix.lower()
    if ext not in ('.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg'):
        return jsonify({'error': 'unsupported type'}), 400
    name = str(uuid.uuid4()) + ext
    dest = SITE_ROOT / 'uploads' / name
    dest.parent.mkdir(exist_ok=True)
    f.save(str(dest))
    return jsonify({'url': f'/uploads/{name}'})

# ── Static site passthrough ───────────────────────────────────────────────────

@app.route('/uploads/<path:filename>')
def serve_upload(filename):
    return send_from_directory(str(SITE_ROOT / 'uploads'), filename)

@app.route('/', defaults={'path': 'index.html'})
@app.route('/<path:path>')
def serve_site(path):
    full = SITE_ROOT / path
    if full.is_dir():
        full = full / 'index.html'
    if full.exists():
        return send_from_directory(str(full.parent), full.name)
    abort(404)

# ── Helpers ───────────────────────────────────────────────────────────────────

def _slugify(text):
    import re
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_-]+', '-', text)
    return text[:80]

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
          <a href="../../index.html">Home</a> <span>/</span>
          <a href="../../resources/index.html">Resources</a> <span>/</span>
          <a href="../../resources/{ct}.html">{ct_label}</a> <span>/</span>
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
          <a href="../../resources/{ct}.html" class="btn btn-ghost btn-sm">← Back to {ct_label}</a>
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
    """Write one static HTML file per published CMS item into resources/{ct}/."""
    out_dir = SITE_ROOT / 'resources' / ct
    out_dir.mkdir(exist_ok=True)

    # Remove stale pages for unpublished / deleted items
    existing = {p.stem for p in out_dir.glob('*.html')}
    items = load_cms(ct)
    published_ids = {i['id'] for i in items if i.get('published')}
    for stem in existing - published_ids:
        (out_dir / f'{stem}.html').unlink(missing_ok=True)

    meta = CMS_TYPES[ct]
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
        with open(out_dir / f'{item["id"]}.html', 'w', encoding='utf-8') as f:
            f.write(html)

def _rebuild_resource_page(ct):
    """Re-inject CMS cards into the static resource listing page and write article files."""
    _generate_article_pages(ct)

    page_map = {
        'blogs':        'resources/blogs.html',
        'case-studies': 'resources/case-studies.html',
        'guides':       'resources/guides.html',
    }
    html_file = SITE_ROOT / page_map[ct]
    if not html_file.exists():
        return

    items = [i for i in load_cms(ct) if i.get('published')]
    items.sort(key=lambda x: x.get('created_at', ''), reverse=True)

    cover_label = CMS_TYPES[ct]['cover_label']
    cards_html = ''
    if items:
        for item in items:
            tags_html = ''.join(
                f'<span>{t}</span><span class="dot"></span>'
                for t in item.get('tags', [])
            ).rstrip('<span class="dot"></span>')
            # Relative link from resources/{ct}.html → resources/{ct}/{id}.html
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
        cards_html = '<p class="lead" style="color:var(--fg-secondary);padding:40px 0;">No published entries yet. Add some from the admin panel.</p>'

    with open(html_file, encoding='utf-8') as f:
        soup = BeautifulSoup(f.read(), 'lxml')

    grid = soup.select_one('.res-grid')
    if grid:
        banner = soup.select_one('.status-banner')
        if banner:
            banner.decompose()
        grid.clear()
        frag = BeautifulSoup(cards_html, 'html.parser')
        for child in list(frag.children):
            grid.append(child)

    with open(html_file, 'w', encoding='utf-8') as f:
        f.write(str(soup))

# ── Article detail page (still served by Flask on 3001 as fallback) ───────────

@app.route('/api/cms/<ct>/<item_id>')
def api_article(ct, item_id):
    """JSON fallback — returns item data for programmatic use."""
    if ct not in CMS_TYPES:
        abort(404)
    items = load_cms(ct)
    item = next((i for i in items if i['id'] == item_id and i.get('published')), None)
    if not item:
        abort(404)
    return jsonify(item)

if __name__ == '__main__':
    print('GTXO Admin running at http://localhost:3001/admin/')
    app.run(port=3001, debug=True)
