# ===================================================================================
# Project: ChatSkLearn
# File: src/services/chunking/content_chunker.py
# Description: Loads content from crawled URLs using LangChain and creates RAG-optimized chunks
# Author: LALAN KUMAR
# Created: [01-11-2025]
# Updated: [01-11-2025]
# LAST MODIFIED BY: LALAN KUMAR [https://github.com/kumar8074]
# Version: 1.1.0
# ===================================================================================

import os
import sys
import json
import re
from pathlib import Path
from bs4 import BeautifulSoup

# Dynamically add the project root directory to sys.path
current_file_path = os.path.abspath(__file__)
project_root = os.path.abspath(os.path.join(current_file_path, "../../../.."))
if project_root not in sys.path:
    sys.path.append(project_root)
    
from src.logger import logging

script_dir = os.path.dirname(os.path.abspath(__file__))

class SkLearnContentLoader:
    """
    Loads scikit-learn documentation content using LangChain's WebBaseLoader
    with code preservation and RAG-optimized chunking
    """
    
    def __init__(self, 
                 urls_file="temp/successful_urls.txt",
                 output_dir="temp/sklearn_scraped_data",
                 chunk_size=900,
                 chunk_overlap=200):
        self.urls_file = urls_file
        self.output_dir = output_dir
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.crawled_data = []
        self.failed_pages = []
        
        # Create output directory
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)
    
    def load_urls(self):
        """Load URLs from the successful_urls.txt file"""
        urls = []
        urls_path = os.path.join(self.urls_file)
        
        if not os.path.exists(urls_path):
            logging.info(f"❌ URLs file not found: {urls_path}")
            logging.info("Please run the crawler first to generate successful_urls.txt")
            return urls
        
        with open(urls_path, 'r') as f:
            urls = [line.strip() for line in f if line.strip()]
        
        logging.info(f"📋 Loaded {len(urls)} URLs from {urls_path}")
        return urls
    
    def classify_page_type(self, url, soup):
        """Classify sklearn documentation page type"""
        url_lower = url.lower()
        
        if '/modules/generated/' in url_lower:
            return 'api_reference'
        elif '/modules/' in url_lower and url_lower.count('/') <= 5:
            return 'user_guide'
        elif '/auto_examples/' in url_lower:
            return 'example'
        elif '/tutorial/' in url_lower:
            return 'tutorial'
        elif 'index.html' in url_lower:
            return 'index'
        else:
            return 'documentation'
    
    def extract_breadcrumbs(self, soup):
        """Extract breadcrumb navigation"""
        breadcrumbs = []
        
        # sklearn-specific breadcrumb patterns
        breadcrumb_selectors = [
            'nav[aria-label*="breadcrumb"]',
            '.breadcrumb',
            '.breadcrumbs',
            'ul.breadcrumb',
            '[class*="breadcrumb"]'
        ]
        
        for selector in breadcrumb_selectors:
            breadcrumb_el = soup.select_one(selector)
            if breadcrumb_el:
                links = breadcrumb_el.find_all('a')
                breadcrumbs = [link.get_text(strip=True) for link in links]
                
                # Add current page
                current = breadcrumb_el.find(['li', 'span'], class_=re.compile('current|active', re.I))
                if current:
                    breadcrumbs.append(current.get_text(strip=True))
                break
        
        return breadcrumbs
    
    def extract_code_blocks(self, soup):
        """Extract and preserve code blocks with metadata"""
        code_blocks = []
        
        # Find all code blocks
        for idx, code_elem in enumerate(soup.find_all(['pre', 'div'], class_=re.compile('highlight|code'))):
            
            # Get the actual code content
            code_tag = code_elem.find('code') or code_elem
            code_text = code_tag.get_text()
            
            if not code_text.strip():
                continue
            
            # Detect language
            language = 'python'  # default for sklearn
            classes = ' '.join(code_elem.get('class', []))
            
            if 'bash' in classes or 'shell' in classes or 'console' in classes:
                language = 'bash'
            elif 'output' in classes or 'highlight-default' in classes:
                language = 'output'
            elif 'python' in classes:
                language = 'python'
            
            # Get context (preceding heading or paragraph)
            context = self._get_code_context(code_elem)
            
            code_blocks.append({
                'index': idx,
                'code': code_text.strip(),
                'language': language,
                'context': context,
                'lines': len(code_text.strip().split('\n'))
            })
            
            # Mark this element so we can handle it specially during chunking
            code_elem['data-code-block-index'] = str(idx)
        
        return code_blocks
    
    def _get_code_context(self, code_elem, max_distance=3):
        """Get context for a code block by looking at preceding elements"""
        context = ""
        current = code_elem
        
        for _ in range(max_distance):
            current = current.find_previous(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p'])
            if current:
                text = current.get_text(strip=True)
                if current.name.startswith('h'):
                    context = text
                    break
                elif len(text) > 20:
                    context = text[:100] + '...' if len(text) > 100 else text
                    break
        
        return context
    
    def extract_api_signature(self, soup):
        """Extract API signature for API reference pages"""
        # Look for class/function signature
        signature = soup.find(['dt', 'dl'], class_=re.compile('sig|signature'))
        if signature:
            return signature.get_text(strip=True)
        
        return None
    
    def clean_html(self, soup):
        """Remove non-content elements while preserving code blocks"""
        if not soup:
            return soup
        
        # Make a copy to avoid modifying the original
        soup_copy = BeautifulSoup(str(soup), 'html.parser')
        
        # Only remove specific non-content elements, be very conservative
        # Remove scripts and styles
        for element in soup_copy.find_all(['script', 'style', 'noscript']):
            element.decompose()
        
        # Remove specific sklearn non-content classes (be very selective)
        non_content_selectors = [
            '.sphx-glr-download-link-note',
            '.sphx-glr-signature', 
            '#searchbox',
            '.headerlink',
            '.viewcode-link'
        ]
        for selector in non_content_selectors:
            for element in soup_copy.select(selector):
                element.decompose()
        
        return soup_copy
    
    def split_text_with_overlap(self, text, chunk_size, overlap):
        """Split text into chunks with overlap"""
        words = text.split()
        chunks = []
        
        i = 0
        while i < len(words):
            # Get chunk
            chunk_words = words[i:i + chunk_size]
            chunk_text = ' '.join(chunk_words)
            
            if chunk_text.strip():
                chunks.append(chunk_text)
            
            # Move forward by (chunk_size - overlap)
            i += (chunk_size - overlap)
            
            # Break if remaining text is too small
            if i >= len(words):
                break
        
        return chunks
    
    def chunk_content_with_code(self, soup, url, metadata, page_type, code_blocks):
        """Create chunks with code block preservation"""
        chunks = []
        
        breadcrumbs = self.extract_breadcrumbs(soup)
        
        # Don't clean too aggressively - just remove scripts/styles
        working_soup = BeautifulSoup(str(soup), 'html.parser')
        for element in working_soup.find_all(['script', 'style', 'noscript']):
            element.decompose()
        
        # Find main content with multiple fallback strategies
        main_content = None
        
        # Strategy 1: Look for sklearn-specific content containers
        sklearn_selectors = [
            'div.body',
            'div.document', 
            'div#main-content',
            'div.main-content',
            'div[role="main"]',
            'main',
            'article',
            'div.bodywrapper',
            'div.documentwrapper',
            'div.content',
            'div.rst-content',
            'section',
            'div#content'
        ]
        
        for selector in sklearn_selectors:
            try:
                main_content = working_soup.select_one(selector)
                if main_content:
                    content_text = main_content.get_text(strip=True)
                    if len(content_text) > 100:
                        #logging.info(f"   ✓ Found content using: {selector} ({len(content_text)} chars)")
                        break
                    else:
                        main_content = None
            except Exception as e:
                continue
        
        # Strategy 2: Look for divs with class containing 'body', 'content', 'main'
        if not main_content:
            for div in working_soup.find_all('div', class_=True):
                class_str = ' '.join(div.get('class', []))
                if any(keyword in class_str.lower() for keyword in ['body', 'content', 'main', 'document']):
                    content_text = div.get_text(strip=True)
                    if len(content_text) > 100:
                        main_content = div
                        #logging.info(f"   ✓ Found content in div with class: {class_str} ({len(content_text)} chars)")
                        break
        
        # Strategy 3: Use body and filter out navigation
        if not main_content:
            main_content = working_soup.body
            if main_content:
                # Remove obvious non-content sections
                for tag in main_content.find_all(['nav', 'header', 'footer', 'aside']):
                    tag.decompose()
                content_text = main_content.get_text(strip=True)
                #logging.info(f"   ✓ Using filtered body tag ({len(content_text)} chars)")
        
        if not main_content:
            #logging.info(f"   ✗ No main_content element found")
            # Debug: Show what divs we have
            all_divs = working_soup.find_all('div', limit=10)
            #logging.info(f"   Debug: Found {len(working_soup.find_all('div'))} divs total")
            if all_divs:
                #logging.info(f"   Debug: First few divs:")
                for i, div in enumerate(all_divs[:5]):
                    classes = div.get('class', [])
                    div_id = div.get('id', '')
                    text_len = len(div.get_text(strip=True))
                    #logging.info(f"     {i+1}. id='{div_id}', class={classes}, text_len={text_len}")
            return chunks
            
        content_length = len(main_content.get_text(strip=True))
        if content_length < 100:
            #logging.info(f"   ✗ Content too short: {content_length} chars")
            return chunks
        
        # Create header chunk
        header_chunk = self._create_header_chunk(metadata, breadcrumbs, url, page_type, soup)
        if header_chunk:
            chunks.append(header_chunk)
        
        # Extract text with markers for code blocks - SIMPLIFIED APPROACH
        content_parts = []
        current_heading = None
        
        # Get all text-bearing elements in order
        for element in main_content.descendants:
            
            # Skip NavigableStrings and non-elements
            if not hasattr(element, 'name') or element.name is None:
                continue
            
            # Skip if inside code (we handle code separately)
            if element.find_parent(['pre', 'code']):
                continue
            
            # Check if this is a code block we've marked
            if element.get('data-code-block-index'):
                code_idx = int(element.get('data-code-block-index'))
                if code_idx < len(code_blocks):
                    content_parts.append({
                        'type': 'code',
                        'content': code_blocks[code_idx],
                        'heading': current_heading
                    })
                continue
            
            # Handle headings
            if element.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                # Only process if it has direct text (not just child elements)
                direct_text = ''.join([str(s) for s in element.strings if str(s).strip()])
                if direct_text and len(direct_text) > 2:
                    current_heading = direct_text.strip()
                    content_parts.append({
                        'type': 'heading',
                        'content': current_heading,
                        'level': element.name
                    })
            
            # Handle paragraphs and list items
            elif element.name in ['p', 'li', 'dt', 'dd']:
                # Get text only from this element (not nested)
                text_parts = []
                for child in element.children:
                    if isinstance(child, str):
                        text_parts.append(child)
                    elif hasattr(child, 'name') and child.name not in ['code', 'pre', 'div', 'section', 'ul', 'ol']:
                        text_parts.append(child.get_text())
                
                text = ' '.join(text_parts).strip()
                if text and len(text) > 15:
                    content_parts.append({
                        'type': 'text',
                        'content': text,
                        'heading': current_heading
                    })
        
        #logging.info(f"   ✓ Collected {len(content_parts)} content parts")
        
        if not content_parts:
            #logging.info(f"   ⚠️ No content parts extracted")
            return chunks
        
        current_chunk_text = []
        current_chunk_codes = []
        current_chunk_heading = None
        word_count = 0
        
        for part in content_parts:
            if part['type'] == 'heading':
                # If we have accumulated content, save it
                if current_chunk_text and word_count >= 100:
                    chunks.append(self._finalize_chunk(
                        text=' '.join(current_chunk_text),
                        heading=current_chunk_heading,
                        url=url,
                        metadata=metadata,
                        breadcrumbs=breadcrumbs,
                        code_blocks=current_chunk_codes,
                        page_type=page_type
                    ))
                    
                    # Start new chunk with overlap
                    overlap_text = ' '.join(current_chunk_text).split()[-self.chunk_overlap:]
                    current_chunk_text = [' '.join(overlap_text)] if overlap_text else []
                    word_count = len(overlap_text)
                    current_chunk_codes = []
                
                current_chunk_heading = part['content']
                current_chunk_text.append(part['content'])
                word_count += len(part['content'].split())
            
            elif part['type'] == 'text':
                current_chunk_text.append(part['content'])
                word_count += len(part['content'].split())
                
                # Check if chunk is large enough
                if word_count >= self.chunk_size:
                    chunks.append(self._finalize_chunk(
                        text=' '.join(current_chunk_text),
                        heading=current_chunk_heading,
                        url=url,
                        metadata=metadata,
                        breadcrumbs=breadcrumbs,
                        code_blocks=current_chunk_codes,
                        page_type=page_type
                    ))
                    
                    # Create overlap
                    overlap_text = ' '.join(current_chunk_text).split()[-self.chunk_overlap:]
                    current_chunk_text = [' '.join(overlap_text)] if overlap_text else []
                    word_count = len(overlap_text)
                    current_chunk_codes = []
            
            elif part['type'] == 'code':
                current_chunk_codes.append(part['content'])
                
                # If we have a lot of code or text, create chunk
                total_code_lines = sum(cb['lines'] for cb in current_chunk_codes)
                if word_count >= self.chunk_size or total_code_lines > 50:
                    chunks.append(self._finalize_chunk(
                        text=' '.join(current_chunk_text),
                        heading=current_chunk_heading,
                        url=url,
                        metadata=metadata,
                        breadcrumbs=breadcrumbs,
                        code_blocks=current_chunk_codes,
                        page_type=page_type
                    ))
                    
                    # Start fresh (code blocks don't overlap)
                    current_chunk_text = []
                    word_count = 0
                    current_chunk_codes = []
        
        # Finalize last chunk
        if current_chunk_text or current_chunk_codes:
            chunks.append(self._finalize_chunk(
                text=' '.join(current_chunk_text),
                heading=current_chunk_heading,
                url=url,
                metadata=metadata,
                breadcrumbs=breadcrumbs,
                code_blocks=current_chunk_codes,
                page_type=page_type
            ))
        
        # If we still have no chunks, try a simple extraction
        if not chunks:
            #logging.info(f"   Attempting simple text extraction...")
            simple_text = main_content.get_text(separator=' ', strip=True)
            if len(simple_text) > 100:
                # Split into chunks
                words = simple_text.split()
                for i in range(0, len(words), self.chunk_size - self.chunk_overlap):
                    chunk_words = words[i:i + self.chunk_size]
                    if len(chunk_words) >= 50:  # Minimum chunk size
                        chunk_text = ' '.join(chunk_words)
                        chunks.append(self._finalize_chunk(
                            text=chunk_text,
                            heading=metadata.get('title'),
                            url=url,
                            metadata=metadata,
                            breadcrumbs=breadcrumbs,
                            code_blocks=[],
                            page_type=page_type
                        ))
                #logging.info(f"   Created {len(chunks)} chunks using simple extraction")
        
        return chunks
    
    def _create_header_chunk(self, metadata, breadcrumbs, url, page_type, soup):
        """Create header chunk with page overview"""
        title = metadata.get('title', '')
        description = metadata.get('description', '')
        
        if not title:
            return None
        
        text_parts = [title]
        
        if description:
            text_parts.append(description)
        
        # For API pages, include signature
        if page_type == 'api_reference':
            signature = self.extract_api_signature(soup)
            if signature:
                text_parts.append(f"Signature: {signature}")
        
        text = '\n'.join(text_parts)
        
        return {
            'type': 'header',
            'heading': title,
            'text': text,
            'enriched_text': self._enrich_context(
                text=text,
                heading=title,
                url=url,
                metadata=metadata,
                breadcrumbs=breadcrumbs,
                page_type=page_type
            ),
            'source_url': url,
            'metadata': metadata,
            'breadcrumbs': breadcrumbs,
            'code_blocks': [],
            'has_code': False,
            'word_count': len(text.split())
        }
    
    def _finalize_chunk(self, text, heading, url, metadata, breadcrumbs, code_blocks, page_type):
        """Finalize chunk with all metadata and code blocks"""
        # Format code blocks for inclusion
        formatted_code = ""
        if code_blocks:
            for cb in code_blocks:
                formatted_code += f"\n\n```{cb['language']}\n{cb['code']}\n```"
        
        full_text = text + formatted_code if formatted_code else text
        
        return {
            'type': 'content',
            'heading': heading,
            'text': text,  # Text without code
            'full_text': full_text,  # Text with code
            'enriched_text': self._enrich_context(
                text=full_text,
                heading=heading,
                url=url,
                metadata=metadata,
                breadcrumbs=breadcrumbs,
                page_type=page_type,
                has_code=len(code_blocks) > 0
            ),
            'source_url': url,
            'metadata': metadata,
            'breadcrumbs': breadcrumbs,
            'code_blocks': code_blocks,
            'has_code': len(code_blocks) > 0,
            'word_count': len(text.split()),
            'total_code_lines': sum(cb['lines'] for cb in code_blocks)
        }
    
    def _enrich_context(self, text, heading, url, metadata, breadcrumbs, page_type, has_code=False):
        """Add contextual information to chunk for better RAG retrieval"""
        context_parts = []
        
        context_parts.append(f"Documentation: scikit-learn")
        
        if metadata.get('title'):
            context_parts.append(f"Page: {metadata['title']}")
        
        if breadcrumbs:
            context_parts.append(f"Location: {' > '.join(breadcrumbs)}")
        
        if heading:
            context_parts.append(f"Section: {heading}")
        
        context_parts.append(f"Type: {page_type.replace('_', ' ').title()}")
        
        if has_code:
            context_parts.append("Contains: Code Examples")
        
        context_header = '\n'.join(context_parts)
        enriched = f"{context_header}\n\n{text}"
        
        return enriched
    
    def process_url(self, url):
        """Process a single URL using direct requests"""
        try:
            #logging.info(f"📄 Processing: {url}")
            
            # Fetch directly with requests for better reliability
            import requests
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            html_content = response.text
            
            if not html_content or len(html_content) < 100:
                #logging.info(f"⚠️  Empty or too short content")
                self.failed_pages.append({'url': url, 'reason': 'Empty content'})
                return
            
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Debug: Check what we got
            if not soup or not soup.body:
                #logging.info(f"   ✗ Invalid HTML structure (no body)")
                self.failed_pages.append({'url': url, 'reason': 'No body tag'})
                return
            
            body_text = soup.body.get_text(strip=True)
            #logging.info(f"   ✓ HTML loaded: {len(html_content)} chars, body: {len(body_text)} chars")
            
            # Extract metadata
            title_tag = soup.find('title')
            title = title_tag.get_text(strip=True) if title_tag else ''
            
            # Fallback to h1
            if not title:
                h1_tag = soup.find('h1')
                title = h1_tag.get_text(strip=True) if h1_tag else 'Untitled'
            
            metadata = {
                'title': title,
                'description': ''
            }
            
            # Check for meta description
            meta_desc = soup.find('meta', {'name': 'description'})
            if meta_desc and meta_desc.get('content'):
                metadata['description'] = meta_desc.get('content', '')
            
            # Classify page type
            page_type = self.classify_page_type(url, soup)
            
            # Extract code blocks BEFORE cleaning
            code_blocks = self.extract_code_blocks(soup)
            
            # Create chunks
            chunks = self.chunk_content_with_code(soup, url, metadata, page_type, code_blocks)
            
            if not chunks:
                #logging.info(f"⚠️  No chunks created for {url}")
                return
            
            page_data = {
                'url': url,
                'page_type': page_type,
                'metadata': metadata,
                'chunks': chunks,
                'total_chunks': len(chunks),
                'total_words': sum(chunk.get('word_count', 0) for chunk in chunks),
                'total_code_blocks': len(code_blocks)
            }
            
            self.crawled_data.append(page_data)
            
            #logging.info(f"✅ Processed: {url}")
            #logging.info(f"   - Chunks: {len(chunks)}, Code blocks: {len(code_blocks)}, Words: {sum(chunk.get('word_count', 0) for chunk in chunks)}")
            
        except Exception as e:
            logging.info(f"❌ Error processing {url}: {e}")
            import traceback
            traceback.print_exc()
            self.failed_pages.append({'url': url, 'reason': str(e)})
    
    def process_all_urls(self, max_pages=None):
        """Process all URLs from the file"""
        urls = self.load_urls()
        
        if not urls:
            logging.info("No URLs to process!")
            return
        
        if max_pages:
            urls = urls[:max_pages]
            logging.info(f"Processing first {max_pages} URLs")
        
        logging.info(f"\n{'='*60}")
        logging.info(f"Starting content loading...")
        logging.info(f"Total URLs to process: {len(urls)}")
        logging.info(f"Chunk size: {self.chunk_size} words")
        logging.info(f"Chunk overlap: {self.chunk_overlap} words")
        logging.info(f"{'='*60}\n")
        
        for idx, url in enumerate(urls, 1):
            #logging.info(f"\n[{idx}/{len(urls)}]", end=" ")
            self.process_url(url)
            
            # Small delay to be respectful
            import time
            time.sleep(0.3)
        
        logging.info(f"\n{'='*60}")
        logging.info(f"Content loading completed!")
        logging.info(f"Total pages processed: {len(self.crawled_data)}")
        logging.info(f"Total pages failed: {len(self.failed_pages)}")
        logging.info(f"Total chunks: {sum(p['total_chunks'] for p in self.crawled_data)}")
        logging.info(f"Total code blocks: {sum(p['total_code_blocks'] for p in self.crawled_data)}")
        logging.info(f"{'='*60}\n")
    
    def save_data(self):
        """Save crawled data in RAG-optimized formats"""
        
        # 1. Save as JSONL for easy streaming
        chunks_file = os.path.join(self.output_dir, "chunks_for_rag.jsonl")
        with open(chunks_file, 'w', encoding='utf-8') as f:
            for page in self.crawled_data:
                for chunk in page['chunks']:
                    chunk['page_type'] = page['page_type']
                    f.write(json.dumps(chunk, ensure_ascii=False) + '\n')
        logging.info(f"✅ Saved chunks for RAG (JSONL): {chunks_file}")
        
        # 2. Save all chunks as JSON
        all_chunks = []
        for page in self.crawled_data:
            for chunk in page['chunks']:
                chunk['page_type'] = page['page_type']
                all_chunks.append(chunk)
        
        all_chunks_file = os.path.join(self.output_dir, "all_chunks.json")
        with open(all_chunks_file, 'w', encoding='utf-8') as f:
            json.dump(all_chunks, f, indent=2, ensure_ascii=False)
        logging.info(f"✅ Saved all chunks (JSON): {all_chunks_file}")
        
        # 3. Save page-level data
        pages_file = os.path.join(self.output_dir, "pages_with_chunks.json")
        with open(pages_file, 'w', encoding='utf-8') as f:
            json.dump(self.crawled_data, f, indent=2, ensure_ascii=False)
        logging.info(f"✅ Saved page-level data: {pages_file}")
        
        # 4. Save statistics
        stats = {
            'total_pages': len(self.crawled_data),
            'total_chunks': sum(p['total_chunks'] for p in self.crawled_data),
            'total_words': sum(p['total_words'] for p in self.crawled_data),
            'total_code_blocks': sum(p['total_code_blocks'] for p in self.crawled_data),
            'avg_chunks_per_page': sum(p['total_chunks'] for p in self.crawled_data) / len(self.crawled_data) if self.crawled_data else 0,
            'pages_by_type': {},
            'chunks_by_type': {},
            'chunks_with_code': sum(1 for p in self.crawled_data for c in p['chunks'] if c.get('has_code')),
            'failed_pages': self.failed_pages,
            'failed_count': len(self.failed_pages),
            'chunk_size': self.chunk_size,
            'chunk_overlap': self.chunk_overlap
        }
        
        for page in self.crawled_data:
            page_type = page['page_type']
            stats['pages_by_type'][page_type] = stats['pages_by_type'].get(page_type, 0) + 1
            
            for chunk in page['chunks']:
                chunk_type = chunk['type']
                stats['chunks_by_type'][chunk_type] = stats['chunks_by_type'].get(chunk_type, 0) + 1
        
        stats_file = os.path.join(self.output_dir, "crawl_statistics.json")
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(stats, f, indent=2, ensure_ascii=False)
        logging.info(f"✅ Saved statistics: {stats_file}")
        
        logging.info(f"\n📊 Summary:")
        logging.info(f"   - Total pages: {stats['total_pages']}")
        logging.info(f"   - Total chunks: {stats['total_chunks']}")
        logging.info(f"   - Total words: {stats['total_words']:,}")
        logging.info(f"   - Total code blocks: {stats['total_code_blocks']}")
        logging.info(f"   - Chunks with code: {stats['chunks_with_code']}")
        logging.info(f"   - Avg chunks/page: {stats['avg_chunks_per_page']:.1f}")
        logging.info(f"   - Failed pages: {stats['failed_count']}")
        logging.info(f"   - Chunk size: {stats['chunk_size']} words")
        logging.info(f"   - Chunk overlap: {stats['chunk_overlap']} words")


def main():
    """Main entry point"""
    import time
    start_time = time.time()
    
    loader = SkLearnContentLoader(
        urls_file="temp/successful_urls.txt",
        output_dir="temp/sklearn_scraped_data",
        chunk_size=1000,
        chunk_overlap=200
    )
    
    logging.info("🚀 Starting scikit-learn content loading with LangChain...")
    loader.process_all_urls(max_pages=None)  # Set max_pages to test with fewer pages
    
    loader.save_data()
    
    duration = time.time() - start_time
    
    logging.info("✅ Content loading completed successfully!")
    logging.info(f"✅ Finished in {duration:.2f} seconds")
    logging.info("\nNext steps:")
    logging.info("1. Load chunks_for_rag.jsonl into your vector database")
    logging.info("2. Generate embeddings for the 'enriched_text' field")
    logging.info("3. Use 'full_text' field to display code examples in responses")
    logging.info("4. Store 'source_url', 'heading', and 'code_blocks' for citations")


if __name__ == "__main__":
    main()