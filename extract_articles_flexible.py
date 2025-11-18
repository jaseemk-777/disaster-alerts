"""
Flexible Article Content Extractor
Modified version of extract_articles.py to work with disaster-specific folder structure
"""

import os
import json
import pandas as pd
from datetime import datetime, timedelta
import logging
import sys
import argparse
from article_scraper import ArticleScraper
import hashlib
import time
from typing import List, Dict, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)


class FlexibleArticleExtractor:
    """Flexible extractor that works with disaster-specific folder structure"""
    
    def __init__(self, disaster_id: str):
        """
        Initialize extractor
        
        Args:
            disaster_id: Disaster identifier (e.g., '2025-cyclone-montha')
        """
        self.disaster_id = disaster_id
        self.base_data_dir = os.path.join("data", disaster_id)
        self.json_output_dir = os.path.join("JSON Output", disaster_id)
        self.json_spare_dir = os.path.join("JSON Output Spare", disaster_id)
        self.logger = logging.getLogger(__name__)
        
        # Create output directories
        os.makedirs(self.json_output_dir, exist_ok=True)
        os.makedirs(self.json_spare_dir, exist_ok=True)
        
        # Initialize scraper
        self.scraper = ArticleScraper(parallelism=1, process_timeout=30)
        
        self.logger.info(f"Initialized extractor for disaster: {disaster_id}")
    
    def extract_all_articles(self, date_range: Optional[tuple] = None):
        """
        Extract full article content from all CSV files
        
        Args:
            date_range: Optional tuple of (start_date, end_date) to filter extraction
        """
        self.logger.info(f"🚀 Starting article extraction for {self.disaster_id}")
        
        # Find all CSV files
        csv_files = self._find_all_csv_files(date_range)
        
        if not csv_files:
            self.logger.warning(f"No CSV files found for {self.disaster_id}")
            return
        
        self.logger.info(f"📂 Found {len(csv_files)} CSV files to process")
        
        # Process all CSV files
        all_articles = []
        
        for i, csv_path in enumerate(csv_files, 1):
            self.logger.info(f"\n{'='*80}")
            self.logger.info(f"Processing CSV {i}/{len(csv_files)}: {csv_path}")
            self.logger.info(f"{'='*80}")
            
            articles = self._extract_from_csv(csv_path)
            all_articles.extend(articles)
            
            # Brief pause between CSVs
            if i < len(csv_files):
                time.sleep(2)
        
        # Clean up scraper
        self.scraper.quit()
        
        if not all_articles:
            self.logger.warning("No articles were successfully extracted")
            return
        
        # Deduplicate across ALL dates
        self.logger.info(f"\n🔄 Deduplicating {len(all_articles)} articles...")
        deduplicated = self._smart_deduplication(all_articles)
        
        # Create statistics
        stats = self._create_statistics(deduplicated)
        
        # Save results
        self._save_results(deduplicated, stats)
        
        self.logger.info(f"\n🎉 Extraction complete!")
        self.logger.info(f"📊 Total articles: {len(deduplicated)}")
        self.logger.info(f"📁 Results saved to: {self.json_output_dir}")
    
    def _find_all_csv_files(self, date_range: Optional[tuple] = None) -> List[str]:
        """
        Find all CSV files in disaster directory
        
        Args:
            date_range: Optional (start_date, end_date) tuple for filtering
        
        Returns:
            List of CSV file paths
        """
        csv_files = []
        
        if not os.path.exists(self.base_data_dir):
            self.logger.error(f"Data directory not found: {self.base_data_dir}")
            return csv_files
        
        # Walk through directory structure
        for root, dirs, files in os.walk(self.base_data_dir):
            for file in files:
                if file.endswith('.csv'):
                    csv_path = os.path.join(root, file)
                    
                    # If date range specified, check if CSV is within range
                    if date_range:
                        csv_date = self._extract_date_from_path(csv_path)
                        if csv_date and date_range[0] <= csv_date <= date_range[1]:
                            csv_files.append(csv_path)
                    else:
                        csv_files.append(csv_path)
        
        return sorted(csv_files)
    
    def _extract_date_from_path(self, path: str) -> Optional[datetime]:
        """Extract date from CSV path"""
        try:
            parts = path.split(os.sep)
            # Expected format: .../YYYY/MM/DD/results.csv
            if len(parts) >= 3:
                year = int(parts[-4])
                month = int(parts[-3])
                day = int(parts[-2])
                return datetime(year, month, day).date()
        except (ValueError, IndexError):
            pass
        return None
    
    def _extract_from_csv(self, csv_path: str) -> List[Dict]:
        """
        Extract full article content from a CSV file
        
        Args:
            csv_path: Path to CSV file
        
        Returns:
            List of article dictionaries
        """
        try:
            df = pd.read_csv(csv_path)
        except Exception as e:
            self.logger.error(f"Failed to read CSV {csv_path}: {e}")
            return []
        
        if "link" not in df.columns:
            self.logger.warning(f"No 'link' column in {csv_path}")
            return []
        
        # Get valid URLs
        urls = []
        for url in df["link"].fillna("").tolist():
            if url and isinstance(url, str) and url.strip().startswith(('http://', 'https://')):
                urls.append(url.strip())
        
        if not urls:
            self.logger.warning(f"No valid URLs in {csv_path}")
            return []
        
        self.logger.info(f"📊 Extracting content from {len(urls)} URLs")
        
        # Extract articles using scraper
        results = self.scraper.getArticles(urls)
        
        # Process results
        articles = []
        
        # Create URL to row mapping
        url_to_row = {url: idx for idx, url in enumerate(df["link"])}
        
        for i, result in enumerate(results):
            if not result or len(result) < 3 or not result[2]:
                continue
            
            original_url = urls[i] if i < len(urls) else None
            if not original_url:
                continue
            
            final_url, article_title, article_text = result[:3]
            detected_language = result[3] if len(result) > 3 else "en"
            
            if not article_text or len(article_text) < 200:
                continue
            
            # Get metadata from CSV
            row_idx = url_to_row.get(original_url)
            if row_idx is not None and row_idx < len(df):
                row = df.iloc[row_idx].to_dict()
            else:
                row = {}
            
            # Create unique ID
            normalized_url = self._normalize_url(final_url)
            article_id = hashlib.md5((normalized_url + (article_title or "")).encode()).hexdigest()
            
            # Build article dictionary
            article = {
                "id": article_id,
                "title": row.get("title", "") or (article_title or ""),
                "final_url": final_url,
                "original_url": original_url,
                "normalized_url": normalized_url,
                "article_text": article_text,
                "article_language": detected_language,
                "metadata": {
                    "csv_date": row.get("date", ""),
                    "csv_source": row.get("source", ""),
                    "csv_summary": row.get("summary", ""),
                    "csv_language": row.get("language", ""),
                    "csv_hazard": row.get("hazard", ""),
                    "csv_keyword": row.get("keyword", ""),
                    "csv_location": row.get("location", ""),
                    "csv_newspaper": row.get("newspaper", ""),
                    "query_type": row.get("query_type", "")
                },
                "disaster_id": self.disaster_id,
                "extraction_timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "extraction_quality": self._assess_quality(article_text)
            }
            
            articles.append(article)
            self.logger.info(f"✅ Extracted: {article['title'][:60]}...")
        
        self.logger.info(f"📈 Successfully extracted {len(articles)}/{len(urls)} articles")
        
        return articles
    
    def _normalize_url(self, url: str) -> str:
        """Normalize URL for deduplication"""
        from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
        import re
        
        try:
            # Handle Google News URLs specially
            if 'news.google.com/rss/articles/' in url:
                article_id_match = re.search(r'/articles/([^?]+)', url)
                if article_id_match:
                    return f"google_news_{article_id_match.group(1)}"
            
            parsed = urlparse(url)
            
            # Remove tracking parameters
            if parsed.query:
                query_params = parse_qs(parsed.query)
                tracking_params = [
                    'utm_source', 'utm_medium', 'utm_campaign', 'utm_content', 'utm_term',
                    'fbclid', 'gclid', '_ga', '_gac', 'ref', 'source', 'medium',
                    'campaign', 'oc'
                ]
                for param in tracking_params:
                    query_params.pop(param, None)
                
                new_query = urlencode(query_params, doseq=True)
                parsed = parsed._replace(query=new_query)
            
            parsed = parsed._replace(fragment='')
            normalized = urlunparse(parsed).lower().rstrip('/')
            
            return normalized
        except Exception as e:
            self.logger.warning(f"Error normalizing URL {url}: {e}")
            return url.lower().rstrip('/')
    
    def _assess_quality(self, text: str) -> str:
        """Assess extraction quality"""
        if not text:
            return "low"
        
        text_length = len(text)
        paragraphs = text.split('\n')
        num_paragraphs = len([p for p in paragraphs if len(p.strip()) > 20])
        
        # Check for HTML artifacts
        html_artifacts = len([c for c in text if c in '<>'])
        has_html = html_artifacts > 10
        
        # Check word diversity
        words = text.split()
        unique_words = set(words)
        word_repetition_ratio = len(unique_words) / len(words) if words else 0
        
        if (text_length > 1500 and num_paragraphs >= 3 and not has_html and 
            word_repetition_ratio > 0.3):
            return "high"
        elif (text_length > 500 and num_paragraphs >= 2 and word_repetition_ratio > 0.2):
            return "medium"
        else:
            return "low"
    
    def _smart_deduplication(self, articles: List[Dict]) -> List[Dict]:
        """
        Smart deduplication across all articles
        
        Args:
            articles: List of article dictionaries
        
        Returns:
            Deduplicated list
        """
        if not articles:
            return []
        
        self.logger.info(f"🔄 Starting deduplication of {len(articles)} articles")
        
        # Step 1: URL deduplication
        url_map = {}
        url_deduplicated = []
        
        for item in articles:
            normalized_url = item.get('normalized_url', '')
            if not normalized_url:
                url_deduplicated.append(item)
                continue
            
            url_hash = hashlib.md5(normalized_url.encode()).hexdigest()
            
            if url_hash not in url_map:
                url_map[url_hash] = item
                url_deduplicated.append(item)
            else:
                # Keep better quality
                existing_quality = url_map[url_hash].get('extraction_quality', 'low')
                current_quality = item.get('extraction_quality', 'low')
                
                quality_order = {'high': 3, 'medium': 2, 'low': 1}
                if quality_order.get(current_quality, 1) > quality_order.get(existing_quality, 1):
                    url_map[url_hash] = item
                    url_deduplicated = [x for x in url_deduplicated if x != url_map[url_hash]]
                    url_deduplicated.append(item)
        
        self.logger.info(f"  Removed {len(articles) - len(url_deduplicated)} URL duplicates")
        
        # Step 2: Content deduplication
        content_map = {}
        content_deduplicated = []
        
        for item in url_deduplicated:
            text = item.get('article_text', '')
            if not text or len(text) < 100:
                content_deduplicated.append(item)
                continue
            
            # Create fingerprint
            text_clean = text.lower()[:500]
            content_hash = hashlib.md5(text_clean.encode()).hexdigest()
            
            if content_hash not in content_map:
                content_map[content_hash] = item
                content_deduplicated.append(item)
        
        self.logger.info(f"  Removed {len(url_deduplicated) - len(content_deduplicated)} content duplicates")
        self.logger.info(f"  Final: {len(content_deduplicated)}/{len(articles)} unique articles")
        
        return content_deduplicated
    
    def _create_statistics(self, articles: List[Dict]) -> Dict:
        """Create statistics about extracted articles"""
        stats = {
            'disaster_id': self.disaster_id,
            'extraction_timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'total_articles': len(articles),
            'by_language': {},
            'by_quality': {},
            'by_date': {},
            'by_location': {},
            'by_keyword': {}
        }
        
        for article in articles:
            # By language
            lang = article.get('article_language', 'unknown')
            stats['by_language'][lang] = stats['by_language'].get(lang, 0) + 1
            
            # By quality
            quality = article.get('extraction_quality', 'unknown')
            stats['by_quality'][quality] = stats['by_quality'].get(quality, 0) + 1
            
            # By date
            date_str = article.get('metadata', {}).get('csv_date', '')
            if date_str:
                try:
                    date_key = date_str.split()[0]  # Get just the date part
                    stats['by_date'][date_key] = stats['by_date'].get(date_key, 0) + 1
                except:
                    pass
            
            # By location
            location = article.get('metadata', {}).get('csv_location', '')
            if location:
                stats['by_location'][location] = stats['by_location'].get(location, 0) + 1
            
            # By keyword
            keyword = article.get('metadata', {}).get('csv_keyword', '')
            if keyword:
                stats['by_keyword'][keyword] = stats['by_keyword'].get(keyword, 0) + 1
        
        return stats
    
    def _save_results(self, articles: List[Dict], stats: Dict):
        """Save results to JSON files"""
        # Separate by quality
        high_quality = [a for a in articles if a.get('extraction_quality') == 'high']
        medium_quality = [a for a in articles if a.get('extraction_quality') == 'medium']
        low_quality = [a for a in articles if a.get('extraction_quality') == 'low']
        combined_quality = high_quality + medium_quality
        
        # Main output: Combined high + medium
        if combined_quality:
            main_file = os.path.join(self.json_output_dir, "articles_combined.json")
            with open(main_file, 'w', encoding='utf-8') as f:
                json.dump(combined_quality, f, ensure_ascii=False, indent=2)
            self.logger.info(f"💾 Main output: {main_file} ({len(combined_quality)} articles)")
        
        # Spare outputs
        spare_files = {
            'articles_all.json': articles,
            'articles_high_quality.json': high_quality,
            'articles_medium_quality.json': medium_quality,
            'articles_low_quality.json': low_quality,
            'extraction_stats.json': stats
        }
        
        for filename, data in spare_files.items():
            if data:  # Only save if there's data
                spare_file = os.path.join(self.json_spare_dir, filename)
                with open(spare_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                
                if isinstance(data, list):
                    self.logger.info(f"💾 Spare output: {spare_file} ({len(data)} articles)")
                else:
                    self.logger.info(f"💾 Spare output: {spare_file}")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Extract full article content for disaster')
    parser.add_argument('--disaster-id', type=str, required=True,
                       help='Disaster ID (e.g., 2025-cyclone-montha)')
    parser.add_argument('--start-date', type=str,
                       help='Start date in DD/MM/YYYY format')
    parser.add_argument('--end-date', type=str,
                       help='End date in DD/MM/YYYY format')
    
    args = parser.parse_args()
    
    # Parse dates if provided
    date_range = None
    if args.start_date and args.end_date:
        try:
            start_date = datetime.strptime(args.start_date, '%d/%m/%Y').date()
            end_date = datetime.strptime(args.end_date, '%d/%m/%Y').date()
            date_range = (start_date, end_date)
        except ValueError:
            print("❌ Invalid date format. Use DD/MM/YYYY")
            sys.exit(1)
    
    # Create extractor
    extractor = FlexibleArticleExtractor(args.disaster_id)
    
    # Extract articles
    extractor.extract_all_articles(date_range)


if __name__ == "__main__":
    main()