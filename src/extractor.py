import aiohttp
from bs4 import BeautifulSoup
import asyncio
import logging
from urllib.parse import urljoin, urlparse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def fetch_html(session, url):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        async with session.get(url, timeout=15, headers=headers) as response:
            response.raise_for_status()
            return await response.text()
    except Exception as e:
        logger.error(f"Error fetching {url}: {e}")
        return None

def get_nearest_category(tag):
    """
    Finds the nearest preceding heading or span with 'title' in its class.
    """
    def is_category_node(node):
        if node.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            return True
        if node.name == 'span' or node.name == 'div':
            classes = node.get('class', [])
            if any(c for c in classes if 'title' in c.lower() or 'header' in c.lower() or 'heading' in c.lower()):
                return True
        return False

    # Look for previous siblings that are headings or specific containers
    curr = tag
    while curr:
        # Handle Dropdown Menu pattern (ul.dropdown-menu with sibling dropdown-toggle)
        if curr.name == 'ul' or (curr.name == 'div' and 'dropdown-menu' in " ".join(curr.get('class', [])).lower()):
            toggle = curr.find_previous_sibling(lambda x: x and any('dropdown-toggle' in c.lower() for c in x.get('class', [])))
            if toggle:
                return toggle.get_text(strip=True)
            
            # Some structures have toggle as a child of the parent (same level as the menu)
            parent = curr.parent
            if parent:
                toggle = parent.find(lambda x: x and any('dropdown-toggle' in c.lower() for c in x.get('class', [])), recursive=False)
                if toggle and toggle != curr:
                    return toggle.get_text(strip=True)

        # Check siblings for standard headings or structural titles
        sibling = curr.find_previous_sibling(is_category_node)
        if sibling:
            return sibling.get_text(strip=True)
            
        # Check parent
        parent = curr.parent
        if not parent or parent.name == 'body' or parent.name == 'html':
            break
            
        # Check if parent is a category node itself
        if is_category_node(parent):
            return parent.get_text(strip=True)
            
        curr = parent
        
    return "General"

def extract_structural_links(html, base_url):
    if not html:
        return {}
    
    soup = BeautifulSoup(html, 'html.parser')
    domain = urlparse(base_url).netloc
    
    # Structure: { category: [ { text: "", url: "" } ] }
    link_tree = {}
    
    # We look for links in header, footer, and main body
    # But usually, it's safer to just iterate all <a> tags and find their context
    for a in soup.find_all('a', href=True):
        href = a['href']
        text = a.get_text(separator=' ', strip=True)
        
        # Resolve relative URLs
        full_url = urljoin(base_url, href)
        
        # Clean URL: Strip parameters but keep segments/fragments
        parsed_clean = urlparse(full_url)
        full_url = f"{parsed_clean.scheme}://{parsed_clean.netloc}{parsed_clean.path}"
        if parsed_clean.fragment:
            full_url += f"#{parsed_clean.fragment}"

        # Cleaned URL metadata
        parsed_full = urlparse(full_url)
        
        # Lenient Domain Matching: Allow same root domain (including subdomains)
        root_domain = ".".join(domain.split('.')[-2:]) if len(domain.split('.')) > 1 else domain
        full_url_domain = parsed_full.netloc
        
        is_internal = (
            full_url_domain == domain or 
            full_url_domain.endswith("." + root_domain) or
            "docs" in full_url_domain
        )

        if not is_internal and parsed_full.netloc:
            # Skip truly external links if they don't seem related to docs
            continue
        
        if full_url.startswith('javascript:') or full_url.startswith('mailto:'):
            continue

        if not text:
            # Try to find an aria-label or title if text is empty (e.g. icon links)
            text = a.get('aria-label') or a.get('title') or "Link"

        category = get_nearest_category(a)
        
        # Final fallback for links inside main/article tags if category is still "General"
        if category == "General":
            parent_main = a.find_parent(['main', 'article', 'section'])
            if parent_main:
                # Try to get an ID or a class name for a more specific label if no heading exists
                tag_id = parent_main.get('id')
                tag_class = parent_main.get('class', [parent_main.name])[0]
                category = (tag_id or tag_class).replace('-', ' ').title()

        if category not in link_tree:
            link_tree[category] = []
            
        # Avoid duplicate links in the same category
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
    
    async with aiohttp.ClientSession() as session:
        html = await fetch_html(session, url)
        if html:
            link_tree = extract_structural_links(html, url)
            backend_results["link_tree"] = link_tree
            
    return backend_results
