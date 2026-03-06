from bs4 import BeautifulSoup
import asyncio
import logging
import re
from urllib.parse import urljoin, urlparse
from playwright.async_api import async_playwright

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Link text that carries no real meaning on its own
GENERIC_LINK_TEXTS = frozenset([
    'learn more', 'read more', 'click here', 'here', 'more', 'view',
    'view all', 'see more', 'find out more', 'get started', 'start now',
    'start', 'explore', 'discover', 'see all', 'show more', 'details',
    'more details', 'view details', 'read', 'continue', 'continue reading',
    'link', 'go', 'visit', 'open', 'download', 'watch', 'listen', 'play',
    'sign up', 'log in', 'login', 'register', 'try now', 'try it', 'try',
    'try free', 'get access', 'get started for free', 'apply', 'apply now',
    'contact us', 'get in touch', 'subscribe', 'learn', 'see', 'check it out', 'hub menu'
])

HEADING_TAGS = ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']

# Matches any class name that looks like a nav/header/menu/dropdown container
NAV_CONTAINER_RE = re.compile(
    r'(?:^|[-_\s])'
    r'(?:nav|navbar|navigation|header|menu|menubar|mega[-_]?menu|'
    r'site[-_]?nav|top[-_]?nav|main[-_]?nav|primary[-_]?nav|'
    r'side[-_]?nav|sidebar|header[-_]?nav|nav[-_]?bar|nav[-_]?menu|'
    r'nav[-_]?wrapper|nav[-_]?container|nav[-_]?links|nav[-_]?list|'
    r'header[-_]?wrapper|header[-_]?container|header[-_]?menu|'
    r'dropdown|drop[-_]?down|dropdown[-_]?menu|dropdown[-_]?content|'
    r'dropdown[-_]?list|dropdown[-_]?nav|dropdown[-_]?wrapper|'
    r'flyout|fly[-_]?out|flyout[-_]?menu|submenu|sub[-_]?menu|'
    r'popover[-_]?menu|popup[-_]?menu|overlay[-_]?menu|panel[-_]?menu)'
    r'(?:[-_\s]|$)',
    re.IGNORECASE
)

def _classes_match_nav(node):
    """Returns True if any class on the node looks like a nav/header/menu container."""
    return bool(NAV_CONTAINER_RE.search(' '.join(node.get('class', []))))

def _label_for_nav_container(node):
    """Derive a human-readable label from a nav/header container element."""
    aria = node.get('aria-label', '').strip()
    if aria:
        return aria
    node_id = node.get('id', '').strip()
    if node_id:
        return node_id.replace('-', ' ').replace('_', ' ').title()
    heading = node.find(HEADING_TAGS)
    if heading:
        text = heading.get_text(strip=True)
        if text:
            return text
    classes = node.get('class', [])
    if classes:
        label = classes[0].replace('-', ' ').replace('_', ' ').strip()
        if label:
            return label.title()
    return None

async def fetch_html(url):
    """
    Fetches fully-rendered HTML using a headless Chromium browser via Playwright.
    Waits for network activity to settle so JS-rendered nav menus are included.
    """
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            await page.goto(url, wait_until='networkidle', timeout=30000)
            html = await page.content()
            await browser.close()
            return html
    except Exception as e:
        logger.error(f"Error fetching {url}: {e}")
        return None

def find_contextual_heading(tag):
    """
    For generic-text links ("learn more", etc.), find the most relevant heading
    by searching upward through container boundaries (card, section, li, article).
    Returns heading text or None.
    """
    # 1. The link might wrap a heading directly
    inner = tag.find(HEADING_TAGS)
    if inner:
        return inner.get_text(strip=True)

    # 2. Walk up the DOM, stopping at meaningful container boundaries
    CONTAINER_BOUNDARIES = ('article', 'section', 'li', 'aside', 'div', 'main')
    curr = tag.parent
    depth = 0

    while curr and curr.name not in ('body', 'html') and depth < 8:
        # Headings that are direct children of this container (non-recursive first)
        for child in curr.children:
            if hasattr(child, 'name') and child.name in HEADING_TAGS:
                text = child.get_text(strip=True)
                if text:
                    return text

        # Any heading anywhere inside this container
        heading = curr.find(HEADING_TAGS)
        if heading:
            text = heading.get_text(strip=True)
            if text:
                return text

        # Stop expanding past hard semantic boundaries
        if curr.name in ('article', 'section', 'li', 'main', 'aside'):
            break

        curr = curr.parent
        depth += 1

    # 3. Last resort: nearest preceding heading anywhere in the document
    for heading in tag.find_all_previous(HEADING_TAGS):
        text = heading.get_text(strip=True)
        if text:
            return text

    return None

def get_nearest_category(tag):
    """
    Finds the most relevant category label for a link by traversing up the DOM.
    Handles: semantic landmarks (nav/header/footer), aria-labels, dropdown menus,
    and standard heading siblings.
    """
    def is_title_node(node):
        if node.name in HEADING_TAGS:
            return True
        if node.name in ('span', 'div', 'p'):
            classes = node.get('class', [])
            if any('title' in c.lower() or 'header' in c.lower() or 'heading' in c.lower() for c in classes):
                return True
        return False

    curr = tag
    while curr:
        # --- Semantic landmark shortcuts ---
        if curr.name == 'footer' or curr.get('role') == 'contentinfo':
            return "Footer"

        if curr.name == 'header' or curr.get('role') == 'banner':
            # Prefer an aria-label on the header, otherwise generic label
            aria = curr.get('aria-label', '').strip()
            return aria if aria else "Header Navigation"

        # Named nav elements  (<nav aria-label="Products">)
        if curr.name == 'nav' or curr.get('role') == 'navigation':
            aria = curr.get('aria-label', '').strip()
            if aria:
                return aria
            # Fall through to let headings/titles inside the nav be found

        # --- Dropdown menu pattern ---
        if curr.name in ('ul', 'ol') or (
            curr.name == 'div' and 'dropdown-menu' in ' '.join(curr.get('class', [])).lower()
        ):
            # Sibling toggle button
            toggle = curr.find_previous_sibling(
                lambda x: x and any('dropdown-toggle' in c.lower() for c in x.get('class', []))
            )
            if toggle:
                return toggle.get_text(strip=True)
            # Toggle as sibling of parent
            parent = curr.parent
            if parent:
                toggle = parent.find(
                    lambda x: x and any('dropdown-toggle' in c.lower() for c in x.get('class', [])),
                    recursive=False
                )
                if toggle and toggle != curr:
                    return toggle.get_text(strip=True)

        # --- Regex-based nav/header/menu container (catches custom class names) ---
        if _classes_match_nav(curr):
            label = _label_for_nav_container(curr)
            if label:
                return label

        # --- Preceding sibling heading or title node ---
        sibling = curr.find_previous_sibling(is_title_node)
        if sibling:
            return sibling.get_text(strip=True)

        # --- aria-label on a meaningful container ---
        if curr.name in ('section', 'article', 'aside', 'div', 'nav'):
            aria = curr.get('aria-label', '').strip()
            if aria:
                return aria

        # --- Parent is itself a title node ---
        parent = curr.parent
        if not parent or parent.name in ('body', 'html'):
            break
        if is_title_node(parent):
            return parent.get_text(strip=True)

        curr = parent

    return "General"

def extract_structural_links(html, base_url):
    if not html:
        return {}

    soup = BeautifulSoup(html, 'html.parser')
    domain = urlparse(base_url).netloc

    # Pre-collect every <a> that lives inside a nav/header container so we
    # never drop them during domain filtering (hidden dropdowns, mega-menus, etc.)
    nav_link_ids: set[int] = set()
    nav_selector_tags = ['header', 'nav', 'footer']
    nav_containers = soup.find_all(
        lambda el: el.name and (
            el.name in nav_selector_tags or
            el.get('role') in ('navigation', 'banner', 'contentinfo') or
            _classes_match_nav(el)
        )
    )
    for container in nav_containers:
        for a in container.find_all('a', href=True):
            nav_link_ids.add(id(a))

    # Structure: { category: [ { text: "", url: "" } ] }
    link_tree = {}

    for a in soup.find_all('a', href=True):
        href = a['href']
        text = a.get_text(separator=' ', strip=True)

        # Resolve relative URLs
        full_url = urljoin(base_url, href)

        # Strip query params but keep path and fragment
        parsed_clean = urlparse(full_url)
        full_url = f"{parsed_clean.scheme}://{parsed_clean.netloc}{parsed_clean.path}"
        if parsed_clean.fragment:
            full_url += f"#{parsed_clean.fragment}"

        parsed_full = urlparse(full_url)

        if full_url.startswith('javascript:') or full_url.startswith('mailto:'):
            continue

        # Lenient domain matching: same root domain (including subdomains)
        root_domain = ".".join(domain.split('.')[-2:]) if len(domain.split('.')) > 1 else domain
        full_url_domain = parsed_full.netloc

        is_internal = (
            full_url_domain == domain or
            full_url_domain.endswith("." + root_domain) or
            "docs" in full_url_domain
        )

        # Nav/header links are always kept regardless of domain
        is_nav_link = id(a) in nav_link_ids
        if not is_internal and parsed_full.netloc and not is_nav_link:
            continue

        # Resolve empty text via aria-label / title attribute
        if not text:
            text = a.get('aria-label') or a.get('title') or ""

        # For generic phrases like "learn more", find the contextual heading instead
        if not text or text.lower().strip() in GENERIC_LINK_TEXTS:
            contextual = find_contextual_heading(a)
            if contextual:
                text = contextual
            elif not text:
                text = "Link"

        category = get_nearest_category(a)

        # Fallback: use the nearest semantic container id/class as category
        if category == "General":
            container = a.find_parent(['main', 'article', 'section'])
            if container:
                tag_id = container.get('id', '').strip()
                tag_class = (container.get('class') or [container.name])[0]
                label = (tag_id or tag_class).replace('-', ' ').replace('_', ' ').strip()
                if label and label.lower() not in ('main', 'body', 'div'):
                    category = label.title()

        if category not in link_tree:
            link_tree[category] = []

        # Deduplicate by URL within the same category
        if not any(l['url'] == full_url for l in link_tree[category]):
            link_tree[category].append({
                "text": text,
                "url": full_url
            })

    return link_tree

async def process_single_page(url):
    backend_results = {
        "url": url,
        "link_tree": {}
    }

    html = await fetch_html(url)
    if html:
        link_tree = extract_structural_links(html, url)
        backend_results["link_tree"] = link_tree

    return backend_results
