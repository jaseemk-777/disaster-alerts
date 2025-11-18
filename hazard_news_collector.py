"""
Hazard News Collector - Global Flexible Implementation
Replaces monsoon.py with configurable hazard-based collection
"""

from datetime import datetime, timedelta
import pytz
import os
import pandas as pd
import time
import pygooglenews
import logging
import re
from typing import List, Dict, Optional, Tuple
from config_handler import HazardConfig
from query_generator import QueryGenerator
from smart_google_news_handler import smart_handler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)


class HazardNewsCollector:
    """Flexible news collector for any hazard type and location"""
    
    def __init__(self, config: HazardConfig):
        """
        Initialize collector with configuration
        
        Args:
            config: HazardConfig instance with all parameters
        """
        self.config = config
        self.query_generator = QueryGenerator(config)
        self.logger = logging.getLogger(__name__)
        self.smart_handler = smart_handler
        
        # Setup output directory
        self.output_dir = os.path.join("data", self.config.disaster_id)
        os.makedirs(self.output_dir, exist_ok=True)
        
        self.logger.info(f"Initialized collector for disaster: {self.config.disaster_id}")
    
    def collect_all_news(self, use_smart_queries: bool = True, max_queries_per_lang: int = 50):
        """
        Collect news from all sources
        
        Args:
            use_smart_queries: If True, uses intelligent query limiting
            max_queries_per_lang: Maximum queries per language (if using smart queries)
        """
        self.logger.info(f"🚀 Starting news collection for {self.config.disaster_id}")
        self.config.print_summary()
        
        all_articles = []
        
        # Step 1: Collect from Google News queries
        if use_smart_queries:
            queries = self.query_generator.generate_smart_queries(max_queries_per_lang)
        else:
            queries = self.query_generator.generate_all_queries()
        
        self.query_generator.print_query_summary(queries)
        
        # Confirm before proceeding
        proceed = input("\n▶️ Proceed with collection? (y/n): ").strip().lower()
        if proceed != 'y':
            self.logger.info("Collection cancelled by user")
            return []
        
        google_articles = self._collect_from_google_news(queries)
        all_articles.extend(google_articles)
        
        # Step 2: Collect from specific links
        if self.config.specific_links:
            self.logger.info(f"\n📎 Processing {len(self.config.specific_links)} specific links...")
            specific_articles = self._collect_from_specific_links()
            all_articles.extend(specific_articles)
        
        # Step 3: Save results
        self._save_results(all_articles)
        
        return all_articles
    
    def _collect_from_google_news(self, queries: List[Dict]) -> List[Dict]:
        """Collect articles using Google News queries"""
        all_articles = []
        
        self.logger.info(f"\n🔍 Executing {len(queries)} Google News queries...")
        
        # Group queries by language for better organization
        queries_by_lang = {}
        for query in queries:
            lang = query['lang_code']
            if lang not in queries_by_lang:
                queries_by_lang[lang] = []
            queries_by_lang[lang].append(query)
        
        total_processed = 0
        
        for lang_code, lang_queries in queries_by_lang.items():
            self.logger.info(f"\n📰 Processing {len(lang_queries)} queries for language: {lang_code}")
            
            # Use country codes from configuration
            country_codes = self.config.country_codes if self.config.country_codes else ['IN']
            self.logger.info(f"🌍 Using country codes: {', '.join(country_codes)}")
            
            # Initialize Google News for specified countries
            gn_instances = {}
            
            for country in country_codes:
                try:
                    gn_instances[country] = pygooglenews.GoogleNews(lang=lang_code, country=country)
                    self.logger.info(f"   ✅ Initialized Google News for {country}")
                except Exception as e:
                    self.logger.warning(f"   ⚠️ Could not initialize Google News for {country}: {e}")
            
            if not gn_instances:
                self.logger.error(f"Could not initialize Google News for any country")
                continue
            
            # Start with first specified country
            primary_country = country_codes[0] if country_codes else 'IN'
            gn = gn_instances.get(primary_country, list(gn_instances.values())[0])
            current_country = primary_country if primary_country in gn_instances else list(gn_instances.keys())[0]
            
            self.logger.info(f"🎯 Primary country: {current_country}")
            
            for i, query_dict in enumerate(lang_queries, 1):
                query = query_dict['query']
                total_processed += 1
                
                self.logger.info(f"Query {i}/{len(lang_queries)} ({total_processed}/{len(queries)}): {query}")
                
                # Calculate when parameter - use broader window
                date_diff = (self.config.end_date - self.config.start_date).days
                # Add buffer for better results - Google News prefers broader searches
                when_parameter = f'{max(date_diff + 14, 30)}d'  # At least 30 days window
                
                # Use smart search
                results = self.smart_handler.smart_search(
                    gn_instance=gn,
                    query=query,
                    when_parameter=when_parameter,
                    lang_code=lang_code,
                    region=query_dict.get('location', ''),
                    max_retries=4
                )
                
                # If no results and multiple countries specified, try alternatives
                if (not results or 'entries' not in results or not results['entries']) and len(gn_instances) > 1:
                    for alt_country, alt_gn in gn_instances.items():
                        if alt_country == current_country:
                            continue
                        
                        self.logger.info(f"  ℹ️ Trying with country={alt_country}...")
                        
                        alt_results = self.smart_handler.smart_search(
                            gn_instance=alt_gn,
                            query=query,
                            when_parameter=when_parameter,
                            lang_code=lang_code,
                            region=query_dict.get('location', ''),
                            max_retries=2
                        )
                        
                        if alt_results and 'entries' in alt_results and alt_results['entries']:
                            results = alt_results
                            self.logger.info(f"  ✅ Found results with country={alt_country}")
                            break
                elif len(gn_instances) == 1:
                    # Only one country specified, no fallback
                    pass
                
                if not results or 'entries' not in results or not results['entries']:
                    self.logger.info(f"  ℹ️ No results found")
                    continue
                
                total_found = len(results['entries'])
                self.logger.info(f"  ✅ Found {total_found} articles")
                
                # Extract and filter articles
                articles = self._extract_and_filter_articles(
                    results,
                    query_dict
                )
                
                self.logger.info(f"  📅 Filtered to {len(articles)} articles within date range")
                
                all_articles.extend(articles)
                
                # Smart delay between queries
                if i < len(lang_queries):
                    delay = self.smart_handler.adaptive_delay()
                    time.sleep(delay)
            
            # Inter-language delay
            if lang_code != list(queries_by_lang.keys())[-1]:
                inter_lang_delay = self.smart_handler.adaptive_delay() * 1.5
                self.logger.info(f"⏳ Inter-language delay: {inter_lang_delay:.1f}s")
                time.sleep(inter_lang_delay)
        
        self.logger.info(f"\n✅ Google News collection complete: {len(all_articles)} articles collected")
        
        return all_articles
    
    def _extract_and_filter_articles(self, results: Dict, query_metadata: Dict) -> List[Dict]:
        """
        Extract articles from results with LENIENT date filtering
        
        Args:
            results: Google News results
            query_metadata: Metadata about the query
        
        Returns:
            List of article dictionaries
        """
        articles = []
        
        for entry in results.get('entries', []):
            # Extract basic info
            title = entry.title
            link = entry.link
            summary = entry.summary if hasattr(entry, 'summary') else ""
            source = ""
            if hasattr(entry, 'source') and hasattr(entry.source, 'title'):
                source = entry.source.title
            
            # Try multiple date extraction strategies
            article_date = None
            ist_date_str = None
            
            # Strategy 1: Try published date from entry
            if hasattr(entry, 'published'):
                try:
                    ist_date_str = self._convert_gmt_to_ist(entry.published)
                    ist_dt = datetime.strptime(ist_date_str, "%Y-%m-%d %H:%M:%S")
                    article_date = ist_dt.date()
                except:
                    pass
            
            # Strategy 2: Try URL date extraction
            if not article_date:
                article_date = self._extract_date_from_url(link)
                if article_date:
                    ist_date_str = article_date.strftime("%Y-%m-%d") + " 12:00:00"
            
            # Strategy 3: If still no date, use a more lenient window
            if not article_date:
                # Log but don't immediately reject
                self.logger.debug(f"Could not determine date for: {title[:50]}...")
                # Use today's date as fallback for now
                article_date = datetime.now().date()
                ist_date_str = article_date.strftime("%Y-%m-%d") + " 12:00:00"
            
            # LENIENT date filtering - allow 7 days buffer on each side
            buffer_days = 7
            lenient_start = self.config.start_date - timedelta(days=buffer_days)
            lenient_end = self.config.end_date + timedelta(days=buffer_days)
            
            if article_date < lenient_start or article_date > lenient_end:
                self.logger.debug(f"Article date {article_date} outside lenient range {lenient_start} to {lenient_end}")
                continue
            
            # Content relevance check - make more lenient
            combined_text = f"{title} {summary}".lower()
            hazard = query_metadata.get('hazard', '').lower()
            
            # At minimum, hazard name should appear
            if hazard and hazard not in combined_text:
                # Also check for partial matches
                hazard_words = hazard.split()
                if not any(word in combined_text for word in hazard_words if len(word) > 3):
                    self.logger.debug(f"Article doesn't mention hazard: {title[:50]}...")
                    continue
            
            # Create article dictionary
            article = {
                'title': title,
                'link': link,
                'date': ist_date_str,
                'source': source,
                'summary': summary,
                'language': query_metadata['lang_code'],
                'hazard': query_metadata['hazard'],
                'keyword': query_metadata.get('keyword', ''),
                'location': query_metadata.get('location', ''),
                'newspaper': query_metadata.get('newspaper', {}).get('name', '') if query_metadata.get('newspaper') else '',
                'query_type': query_metadata.get('type', 'unknown'),
                'disaster_id': self.config.disaster_id
            }
            
            articles.append(article)
        
        return articles
    
    def _collect_from_specific_links(self) -> List[Dict]:
        """Collect articles from specific URLs provided by user"""
        articles = []
        
        for i, link in enumerate(self.config.specific_links, 1):
            self.logger.info(f"Processing specific link {i}/{len(self.config.specific_links)}: {link}")
            
            try:
                # Try to extract article metadata
                article = self._extract_article_from_url(link)
                if article:
                    articles.append(article)
                    self.logger.info(f"  ✅ Successfully extracted")
                else:
                    self.logger.warning(f"  ⚠️ Could not extract article")
            except Exception as e:
                self.logger.error(f"  ❌ Error: {e}")
            
            # Brief delay between links
            time.sleep(1)
        
        return articles
    
    def _extract_article_from_url(self, url: str) -> Optional[Dict]:
        """
        Extract article information from a specific URL with multiple strategies
        
        Args:
            url: Article URL
        
        Returns:
            Article dictionary or None
        """
        import requests
        from bs4 import BeautifulSoup
        import random
        
        # Rotate user agents to avoid detection
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        ]
        
        try:
            # Use rotating user agent and comprehensive headers
            headers = {
                'User-Agent': random.choice(user_agents),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Cache-Control': 'max-age=0',
                'DNT': '1'
            }
            
            # Add referer for certain sites
            if 'ndtv.com' in url:
                headers['Referer'] = 'https://www.google.com/'
            
            # Create session for cookies
            session = requests.Session()
            
            # First try: Regular request with session
            response = session.get(url, headers=headers, timeout=25, allow_redirects=True)
            
            if response.status_code == 403:
                # Try with different user agent
                self.logger.info(f"  Got 403, trying with different user agent...")
                headers['User-Agent'] = random.choice(user_agents)
                time.sleep(2)  # Wait before retry
                response = session.get(url, headers=headers, timeout=25, allow_redirects=True)
            
            if response.status_code != 200:
                self.logger.warning(f"  HTTP {response.status_code} for {url}")
                
                # Last resort: Try with article_scraper
                if response.status_code == 403:
                    self.logger.info(f"  Trying with article_scraper as fallback...")
                    from article_scraper import ArticleScraper
                    scraper = ArticleScraper(parallelism=1, process_timeout=30)
                    results = scraper.getArticles([url])
                    scraper.quit()
                    
                    if results and results[0] and len(results[0]) >= 3:
                        final_url, article_title, article_text = results[0][:3]
                        detected_language = results[0][3] if len(results[0]) > 3 else "en"
                        
                        if article_text and len(article_text) > 200:
                            self.logger.info(f"  ✅ Extracted via article_scraper: {article_title[:60]}...")
                            
                            # Use current date as we couldn't get it from the page
                            article_date = datetime.now().date()
                            
                            # Get first hazard name
                            lang_code = detected_language if detected_language in self.config.languages else self.config.languages[0] if self.config.languages else 'en'
                            hazard_names = self.config.hazard_names.get(lang_code, self.config.hazard_names.get('en', ['Unknown']))
                            hazard = hazard_names[0] if hazard_names else 'Unknown'
                            
                            return {
                                'title': article_title,
                                'link': url,
                                'date': article_date.strftime("%Y-%m-%d %H:%M:%S"),
                                'source': self._extract_domain(url),
                                'summary': article_text[:500],
                                'language': detected_language,
                                'hazard': hazard,
                                'keyword': 'specific_link',
                                'location': '',
                                'newspaper': '',
                                'query_type': 'specific_link',
                                'disaster_id': self.config.disaster_id
                            }
                
                return None
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract title - multiple strategies
            title = None
            
            # Strategy 1: h1 tag
            h1_tags = soup.find_all('h1')
            for h1 in h1_tags:
                text = h1.get_text().strip()
                if len(text) > 10 and len(text) < 300:
                    title = text
                    break
            
            # Strategy 2: og:title meta tag
            if not title:
                og_title = soup.find('meta', property='og:title')
                if og_title and og_title.get('content'):
                    title = og_title['content'].strip()
            
            # Strategy 3: title tag
            if not title:
                title_tag = soup.find('title')
                if title_tag:
                    title = title_tag.get_text().strip()
                    # Clean common suffixes
                    for suffix in [' - The Hindu', ' - NDTV', ' - Times of India', ' | The Hindu', ' | NDTV']:
                        if title.endswith(suffix):
                            title = title[:-len(suffix)].strip()
            
            if not title or len(title) < 10:
                self.logger.warning(f"  Could not extract valid title from {url}")
                return None
            
            # Extract date - use lenient approach
            article_date = self._extract_date_from_soup(soup, url)
            
            # For specific links, use extracted date regardless of configured range
            # User explicitly wants these articles
            if not article_date:
                # Use current date as fallback
                article_date = datetime.now().date()
                self.logger.info(f"  Using current date as fallback for {url}")
            else:
                self.logger.info(f"  Extracted date: {article_date}")
            
            # Extract summary/content - multiple strategies
            summary = self._extract_summary_from_soup(soup)
            
            # If summary is too short, try to extract more content
            if len(summary) < 100:
                # Try to find article body
                article_body = None
                for selector in ['article', '.article-content', '.story-content', '#story-content', '.post-content']:
                    article_body = soup.select_one(selector)
                    if article_body:
                        paragraphs = article_body.find_all('p')
                        summary = ' '.join([p.get_text().strip() for p in paragraphs[:3]])
                        if len(summary) > 100:
                            break
            
            # Detect language
            lang_code = self._detect_language(f"{title} {summary}")
            
            # If no language detected, use first available from config
            if lang_code == "en" and self.config.languages:
                lang_code = self.config.languages[0]
            
            # Get first hazard name for this language or default to English
            hazard_names = self.config.hazard_names.get(lang_code, self.config.hazard_names.get('en', ['Unknown']))
            hazard = hazard_names[0] if hazard_names else 'Unknown'
            
            # Create article dict
            article = {
                'title': title,
                'link': url,
                'date': article_date.strftime("%Y-%m-%d %H:%M:%S") if hasattr(article_date, 'strftime') else article_date,
                'source': self._extract_domain(url),
                'summary': summary[:500],  # Limit summary length
                'language': lang_code,
                'hazard': hazard,
                'keyword': 'specific_link',
                'location': '',
                'newspaper': '',
                'query_type': 'specific_link',
                'disaster_id': self.config.disaster_id
            }
            
            self.logger.info(f"  ✅ Extracted: {title[:60]}...")
            return article
            
        except requests.Timeout:
            self.logger.error(f"  ❌ Timeout accessing {url}")
            return None
        except requests.RequestException as e:
            self.logger.error(f"  ❌ Request error for {url}: {e}")
            return None
        except Exception as e:
            self.logger.error(f"  ❌ Error extracting from {url}: {e}")
            import traceback
            self.logger.debug(traceback.format_exc())
            return None
    
    def _is_content_relevant(self, text: str, query_metadata: Dict) -> bool:
        """
        Check if content is relevant to the hazard and keywords
        
        Args:
            text: Combined title and summary text
            query_metadata: Query metadata including hazard and keywords
        
        Returns:
            True if relevant, False otherwise
        """
        if not text:
            return False
        
        text_lower = text.lower()
        
        # Check for hazard name
        hazard = query_metadata.get('hazard', '').lower()
        if hazard and hazard not in text_lower:
            # Be lenient - might be mentioned differently
            pass
        
        # Check for keyword
        keyword = query_metadata.get('keyword', '').lower()
        if keyword and keyword not in text_lower:
            return False
        
        # Check for location if specified
        location = query_metadata.get('location', '').lower()
        if location and location not in text_lower:
            # Be lenient on location
            pass
        
        return True
    
    def _save_results(self, articles: List[Dict]):
        """
        Save collected articles to CSV files organized by date
        
        Args:
            articles: List of article dictionaries
        """
        if not articles:
            self.logger.warning("No articles to save")
            return
        
        self.logger.info(f"\n💾 Saving {len(articles)} articles...")
        
        # Group articles by date
        articles_by_date = {}
        for article in articles:
            try:
                date_obj = datetime.strptime(article['date'], "%Y-%m-%d %H:%M:%S").date()
                date_key = date_obj.strftime("%Y-%m-%d")
                
                if date_key not in articles_by_date:
                    articles_by_date[date_key] = []
                
                articles_by_date[date_key].append(article)
            except Exception as e:
                self.logger.error(f"Error grouping article by date: {e}")
        
        # Save each date's articles
        for date_key, date_articles in articles_by_date.items():
            date_obj = datetime.strptime(date_key, "%Y-%m-%d").date()
            
            # Create directory structure
            dir_path = os.path.join(
                self.output_dir,
                str(date_obj.year),
                f"{date_obj.month:02d}",
                f"{date_obj.day:02d}"
            )
            os.makedirs(dir_path, exist_ok=True)
            
            # Save to CSV
            csv_path = os.path.join(dir_path, 'results.csv')
            
            df = pd.DataFrame(date_articles)
            
            # Remove duplicates
            before_dedup = len(df)
            df = df.drop_duplicates(subset=['link'])
            after_dedup = len(df)
            
            if before_dedup > after_dedup:
                self.logger.info(f"  🔄 Removed {before_dedup - after_dedup} duplicates for {date_key}")
            
            # Save
            df.to_csv(csv_path, index=False, encoding='utf-8')
            self.logger.info(f"  ✅ Saved {len(df)} articles to {csv_path}")
        
        self.logger.info(f"\n✅ All articles saved successfully")
    
    # Helper methods
    def _convert_gmt_to_ist(self, gmt_datetime: str) -> str:
        """Convert GMT datetime to IST"""
        try:
            gmt_format = "%a, %d %b %Y %H:%M:%S %Z"
            gmt = pytz.timezone('GMT')
            ist = pytz.timezone('Asia/Kolkata')
            gmt_dt = datetime.strptime(gmt_datetime, gmt_format)
            gmt_dt = gmt.localize(gmt_dt)
            return gmt_dt.astimezone(ist).strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            return gmt_datetime
    
    def _extract_date_from_url(self, url: str) -> Optional[datetime]:
        """Extract date from URL patterns with more comprehensive matching"""
        patterns = [
            r'/(\d{4})/(\d{1,2})/(\d{1,2})/',  # /2025/10/24/
            r'/(\d{4})-(\d{1,2})-(\d{1,2})/',  # /2025-10-24/
            r'(\d{4})(\d{2})(\d{2})',          # 20251024
            r'article(\d{8})',                 # article20251024
            r'/(\d{2})-(\d{2})-(\d{4})/',      # /24-10-2025/
            r'/(\d{2})(\d{2})(\d{4})/',        # /24102025/
            r'/news/(\d{4})/(\d{1,2})/(\d{1,2})/', # /news/2025/10/24/
            r'(\d{1,2})_(\d{1,2})_(\d{4})',    # 24_10_2025
            r'-(\d{4})(\d{2})(\d{2})-',        # -20251024-
            r'/(\d{4})/(\w+)/(\d{1,2})/',      # /2025/october/24/
        ]
        
        # Month name mapping
        month_names = {
            'january': 1, 'jan': 1,
            'february': 2, 'feb': 2,
            'march': 3, 'mar': 3,
            'april': 4, 'apr': 4,
            'may': 5,
            'june': 6, 'jun': 6,
            'july': 7, 'jul': 7,
            'august': 8, 'aug': 8,
            'september': 9, 'sep': 9, 'sept': 9,
            'october': 10, 'oct': 10,
            'november': 11, 'nov': 11,
            'december': 12, 'dec': 12
        }
        
        for pattern in patterns:
            match = re.search(pattern, url, re.IGNORECASE)
            if match:
                try:
                    groups = match.groups()
                    
                    if len(groups) == 1:  # Single group like 20251024
                        date_str = groups[0]
                        if len(date_str) == 8:
                            year = int(date_str[:4])
                            month = int(date_str[4:6])
                            day = int(date_str[6:8])
                        else:
                            continue
                    elif len(groups) == 3:
                        # Check if middle group is month name
                        if groups[1].lower() in month_names:
                            year = int(groups[0])
                            month = month_names[groups[1].lower()]
                            day = int(groups[2])
                        elif len(groups[0]) == 4:  # Year first
                            year = int(groups[0])
                            month = int(groups[1])
                            day = int(groups[2])
                        elif len(groups[2]) == 4:  # Year last
                            day = int(groups[0])
                            month = int(groups[1])
                            year = int(groups[2])
                        else:
                            continue
                    else:
                        continue
                    
                    # Validate date components
                    if year < 2000 or year > 2030 or month < 1 or month > 12 or day < 1 or day > 31:
                        continue
                        
                    return datetime(year, month, day).date()
                except (ValueError, IndexError):
                    continue
        
        return None
    
    def _extract_date_from_soup(self, soup, url: str) -> Optional[datetime]:
        """Extract date from BeautifulSoup object with comprehensive strategies"""
        # Try URL first (most reliable)
        url_date = self._extract_date_from_url(url)
        if url_date:
            return url_date
        
        # Try multiple meta tag patterns
        meta_selectors = [
            ('property', 'article:published_time'),
            ('property', 'article:published'),
            ('name', 'publishdate'),
            ('name', 'publication_date'),
            ('name', 'date'),
            ('name', 'article:published_time'),
            ('property', 'og:published_time'),
            ('property', 'og:updated_time'),
            ('itemprop', 'datePublished'),
            ('itemprop', 'dateCreated'),
        ]
        
        for attr, value in meta_selectors:
            meta_tag = soup.find('meta', {attr: value})
            if meta_tag and meta_tag.get('content'):
                try:
                    date_str = meta_tag['content']
                    # Handle ISO format dates
                    if 'T' in date_str:
                        date_str = date_str.split('T')[0]
                    # Try multiple date formats
                    for fmt in ['%Y-%m-%d', '%Y/%m/%d', '%d-%m-%Y', '%d/%m/%Y']:
                        try:
                            return datetime.strptime(date_str, fmt).date()
                        except:
                            continue
                except:
                    continue
        
        # Try time tag with datetime attribute
        time_tag = soup.find('time')
        if time_tag and time_tag.get('datetime'):
            try:
                date_str = time_tag['datetime']
                if 'T' in date_str:
                    date_str = date_str.split('T')[0]
                return datetime.strptime(date_str, '%Y-%m-%d').date()
            except:
                pass
        
        # Try common CSS classes for date
        date_selectors = [
            '.publish-date', '.article-date', '.date', '.timestamp',
            '[class*="date"]', '[class*="time"]', '.byline-date',
            '.story-date', '.post-date', '#publish-date'
        ]
        
        for selector in date_selectors:
            date_elem = soup.select_one(selector)
            if date_elem:
                date_text = date_elem.get_text().strip()
                parsed_date = self._parse_date_string_enhanced(date_text)
                if parsed_date:
                    return parsed_date
        
        # Try JSON-LD structured data
        json_ld = soup.find('script', type='application/ld+json')
        if json_ld:
            try:
                import json
                data = json.loads(json_ld.string)
                if isinstance(data, dict):
                    for key in ['datePublished', 'dateCreated', 'uploadDate']:
                        if key in data:
                            date_str = data[key]
                            if 'T' in date_str:
                                date_str = date_str.split('T')[0]
                            return datetime.strptime(date_str, '%Y-%m-%d').date()
            except:
                pass
        
        return None
    
    def _extract_summary_from_soup(self, soup) -> str:
        """Extract summary from BeautifulSoup object"""
        # Try meta description
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc and meta_desc.get('content'):
            return meta_desc['content'].strip()[:300]
        
        # Try first paragraph
        paragraphs = soup.find_all('p')
        for p in paragraphs:
            text = p.get_text().strip()
            if len(text) > 50:
                return text[:300]
        
        return ""
    
    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL"""
        from urllib.parse import urlparse
        try:
            parsed = urlparse(url)
            domain = parsed.netloc
            if domain.startswith('www.'):
                domain = domain[4:]
            return domain
        except:
            return ""
    
    def _detect_language(self, text: str) -> str:
        """Simple language detection"""
        if not text or len(text) < 50:
            return "en"
        
        # Check for common scripts
        scripts = {
            "hi": ('\u0900', '\u097F'),
            "bn": ('\u0980', '\u09FF'),
            "ta": ('\u0B80', '\u0BFF'),
            "te": ('\u0C00', '\u0C7F'),
            "kn": ('\u0C80', '\u0CFF'),
            "ml": ('\u0D00', '\u0D7F'),
        }
        
        for lang, (start, end) in scripts.items():
            count = sum(1 for c in text if start <= c <= end)
            if count > len(text) * 0.15:
                return lang
        
        return "en"
    
    def _parse_date_string_enhanced(self, date_str: str) -> Optional[datetime]:
        """Parse various date string formats with enhanced support"""
        if not date_str:
            return None
            
        # Clean the date string
        date_str = re.sub(r'[^\w\s\-:/,]', '', date_str).strip()
        
        date_formats = [
            '%Y-%m-%d', '%d-%m-%Y', '%m/%d/%Y', '%d/%m/%Y',
            '%B %d, %Y', '%d %B %Y', '%b %d, %Y', '%d %b %Y',
            '%Y-%m-%d %H:%M:%S', '%d-%m-%Y %H:%M:%S',
            '%d %B, %Y', '%B %d %Y', '%d %b, %Y',
            '%Y/%m/%d', '%d.%m.%Y', '%Y.%m.%d'
        ]
        
        for fmt in date_formats:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue
        
        # Try parsing relative dates like "2 days ago"
        if 'ago' in date_str.lower():
            today = datetime.now().date()
            if 'today' in date_str.lower() or '0 day' in date_str.lower():
                return today
            elif 'yesterday' in date_str.lower() or '1 day' in date_str.lower():
                return today - timedelta(days=1)
            elif '2 day' in date_str.lower():
                return today - timedelta(days=2)
            elif '3 day' in date_str.lower():
                return today - timedelta(days=3)
            elif '4 day' in date_str.lower():
                return today - timedelta(days=4)
            elif '5 day' in date_str.lower():
                return today - timedelta(days=5)
            elif '6 day' in date_str.lower():
                return today - timedelta(days=6)
            elif '7 day' in date_str.lower() or 'week' in date_str.lower():
                return today - timedelta(days=7)
        
        return None


def main():
    """Main entry point for news collection"""
    from config_handler import load_config_interactive
    
    # Load configuration
    config = load_config_interactive()
    
    # Create collector
    collector = HazardNewsCollector(config)
    
    # Collect news
    articles = collector.collect_all_news(
        use_smart_queries=True,
        max_queries_per_lang=50
    )
    
    print(f"\n🎉 Collection complete! Collected {len(articles)} articles")
    print(f"📁 Results saved to: {collector.output_dir}")


if __name__ == "__main__":
    main()