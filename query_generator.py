"""
Query Generator for Global Hazard News Extraction
Generates all combinations of search queries with and without news sources
"""

from typing import List, Dict, Tuple
from itertools import product
import logging


class QueryGenerator:
    """Generate search queries for hazard news extraction"""
    
    def __init__(self, config):
        """
        Initialize query generator with configuration
        
        Args:
            config: HazardConfig instance
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
    
    def generate_all_queries(self) -> List[Dict]:
        """
        Generate all query combinations
        
        Returns:
            List of query dictionaries with metadata
        """
        all_queries = []
        
        # Generate queries for each language
        for lang_code in self.config.languages:
            queries = self._generate_queries_for_language(lang_code)
            all_queries.extend(queries)
        
        self.logger.info(f"Generated {len(all_queries)} total queries across {len(self.config.languages)} languages")
        
        return all_queries
    
    def _generate_queries_for_language(self, lang_code: str) -> List[Dict]:
        """Generate all queries for a specific language"""
        queries = []
        
        # Get hazard names for this language
        hazard_names = self.config.hazard_names.get(lang_code, self.config.hazard_names.get('en', []))
        
        # Get keywords for this language
        keywords = self.config.keywords.get(lang_code, self.config.keywords.get('en', []))
        
        # Get newspapers for this language
        newspapers = self.config.newspapers.get(lang_code, [])
        
        # Get locations
        if self.config.locations:
            locations = self.get_locations_for_queries()
        else:
            locations = ['']  # Empty location for broad search
        
        # Get year for queries
        year = str(self.config.start_date.year)
        
        # Strategy 1: Queries WITHOUT news sources (broad search)
        for hazard in hazard_names:
            for keyword in keywords[:10]:  # Limit keywords to avoid explosion
                for location in locations:
                    query_parts = [hazard, keyword]
                    if location:
                        query_parts.append(location)
                    query_parts.append(year)
                    
                    query_string = ' '.join(query_parts)
                    
                    queries.append({
                        'query': query_string,
                        'lang_code': lang_code,
                        'has_newspaper': False,
                        'hazard': hazard,
                        'keyword': keyword,
                        'location': location,
                        'newspaper': None,
                        'type': 'broad'
                    })
        
        # Strategy 2: Queries WITH news sources (targeted search)
        if newspapers:
            for hazard in hazard_names:
                for keyword in keywords[:5]:  # Even more selective for newspaper queries
                    for location in locations[:5] if locations else ['']:  # Limit locations
                        for newspaper in newspapers:
                            query_parts = [hazard, keyword]
                            if location:
                                query_parts.append(location)
                            query_parts.append(newspaper['name'])
                            query_parts.append(year)
                            
                            query_string = ' '.join(query_parts)
                            
                            queries.append({
                                'query': query_string,
                                'lang_code': lang_code,
                                'has_newspaper': True,
                                'hazard': hazard,
                                'keyword': keyword,
                                'location': location,
                                'newspaper': newspaper,
                                'type': 'targeted'
                            })
        
        self.logger.info(f"Generated {len(queries)} queries for language {lang_code}")
        
        return queries
    
    def get_locations_for_queries(self) -> List[str]:
        """
        Get flattened list of locations suitable for queries
        Prioritizes city/village level but includes district and state
        """
        locations = []
        
        for state, state_data in self.config.locations.items():
            # Add state-level
            locations.append(state)
            
            if 'districts' in state_data:
                for district, cities in state_data['districts'].items():
                    # Add district-level
                    locations.append(district)
                    
                    # Add city/village-level
                    locations.extend(cities)
        
        return locations
    
    def generate_smart_queries(self, max_queries_per_lang: int = 50) -> List[Dict]:
        """
        Generate intelligently limited queries to avoid rate limiting
        
        Args:
            max_queries_per_lang: Maximum queries per language
        
        Returns:
            List of prioritized query dictionaries
        """
        all_queries = []
        
        for lang_code in self.config.languages:
            queries = self._generate_smart_queries_for_language(lang_code, max_queries_per_lang)
            all_queries.extend(queries)
        
        self.logger.info(f"Generated {len(all_queries)} smart queries across {len(self.config.languages)} languages")
        
        return all_queries
    
    def _generate_smart_queries_for_language(self, lang_code: str, max_queries: int) -> List[Dict]:
        """Generate smart, limited queries for a specific language"""
        queries = []
        
        # Get hazard names for this language
        hazard_names = self.config.hazard_names.get(lang_code, self.config.hazard_names.get('en', []))
        
        # Get keywords for this language (prioritize first few)
        keywords = self.config.keywords.get(lang_code, self.config.keywords.get('en', []))[:5]
        
        # Get newspapers for this language
        newspapers = self.config.newspapers.get(lang_code, [])
        
        # Get key locations (prioritize major locations)
        if self.config.locations:
            locations = self.get_priority_locations()[:5]  # Top 5 locations
        else:
            locations = ['']
        
        # Don't include year in query - let date filtering handle it
        # year = str(self.config.start_date.year)
        
        # Smart Strategy 1: Hazard only (most broad) - 20% of budget
        hazard_only_budget = max_queries // 5
        for hazard in hazard_names:
            query_string = f"{hazard}"
            queries.append({
                'query': query_string,
                'lang_code': lang_code,
                'has_newspaper': False,
                'hazard': hazard,
                'keyword': '',
                'location': '',
                'newspaper': None,
                'type': 'hazard_only'
            })
            if len(queries) >= hazard_only_budget:
                break
        
        # Smart Strategy 2: Hazard + Top Keywords (no location) - 25% of budget
        broad_budget = max_queries // 4
        remaining_for_broad = broad_budget - len(queries)
        for hazard in hazard_names:
            for keyword in keywords[:remaining_for_broad]:
                query_string = f"{hazard} {keyword}"
                queries.append({
                    'query': query_string,
                    'lang_code': lang_code,
                    'has_newspaper': False,
                    'hazard': hazard,
                    'keyword': keyword,
                    'location': '',
                    'newspaper': None,
                    'type': 'broad_priority'
                })
                if len(queries) >= hazard_only_budget + broad_budget:
                    break
            if len(queries) >= hazard_only_budget + broad_budget:
                break
        
        # Smart Strategy 3: Hazard + Location (no keyword) - 20% of budget
        location_only_budget = max_queries // 5
        for hazard in hazard_names:
            for location in locations[:location_only_budget]:
                if location:
                    query_string = f"{hazard} {location}"
                    queries.append({
                        'query': query_string,
                        'lang_code': lang_code,
                        'has_newspaper': False,
                        'hazard': hazard,
                        'keyword': '',
                        'location': location,
                        'newspaper': None,
                        'type': 'location_only'
                    })
                    if len(queries) >= hazard_only_budget + broad_budget + location_only_budget:
                        break
            if len(queries) >= hazard_only_budget + broad_budget + location_only_budget:
                break
        
        # Smart Strategy 4: Hazard + Keyword + Location - 35% of budget
        location_budget = (max_queries * 35) // 100
        current_count = len(queries)
        for hazard in hazard_names:
            for keyword in keywords[:2]:  # Top 2 keywords
                for location in locations[:3]:  # Top 3 locations
                    if location:
                        query_string = f"{hazard} {keyword} {location}"
                        queries.append({
                            'query': query_string,
                            'lang_code': lang_code,
                            'has_newspaper': False,
                            'hazard': hazard,
                            'keyword': keyword,
                            'location': location,
                            'newspaper': None,
                            'type': 'location_priority'
                        })
                        if len(queries) >= current_count + location_budget:
                            break
                if len(queries) >= current_count + location_budget:
                    break
            if len(queries) >= current_count + location_budget:
                break
        
        return queries[:max_queries]
    
    def get_priority_locations(self) -> List[str]:
        """
        Get priority locations (cities/major districts first)
        """
        priority_locations = []
        
        # First, collect all cities
        for state, state_data in self.config.locations.items():
            if 'districts' in state_data:
                for district, cities in state_data['districts'].items():
                    priority_locations.extend(cities)
        
        # Then, collect districts
        for state, state_data in self.config.locations.items():
            if 'districts' in state_data:
                for district in state_data['districts'].keys():
                    if district not in priority_locations:
                        priority_locations.append(district)
        
        # Finally, add states
        for state in self.config.locations.keys():
            if state not in priority_locations:
                priority_locations.append(state)
        
        return priority_locations
    
    def group_queries_by_type(self, queries: List[Dict]) -> Dict[str, List[Dict]]:
        """Group queries by type for organized execution"""
        grouped = {
            'broad': [],
            'targeted': [],
            'broad_priority': [],
            'location_priority': [],
            'newspaper_priority': []
        }
        
        for query in queries:
            query_type = query.get('type', 'broad')
            if query_type in grouped:
                grouped[query_type].append(query)
        
        return grouped
    
    def estimate_execution_time(self, queries: List[Dict], avg_time_per_query: float = 5.0) -> float:
        """
        Estimate total execution time for queries
        
        Args:
            queries: List of query dictionaries
            avg_time_per_query: Average seconds per query (including delays)
        
        Returns:
            Estimated time in seconds
        """
        return len(queries) * avg_time_per_query
    
    def print_query_summary(self, queries: List[Dict]):
        """Print summary of generated queries"""
        print(f"\n📊 Query Generation Summary")
        print(f"{'='*60}")
        print(f"Total queries: {len(queries)}")
        
        # By language
        by_lang = {}
        for q in queries:
            lang = q['lang_code']
            by_lang[lang] = by_lang.get(lang, 0) + 1
        
        print(f"\nBy language:")
        for lang, count in sorted(by_lang.items()):
            print(f"  {lang}: {count} queries")
        
        # By type
        by_type = {}
        for q in queries:
            qtype = q.get('type', 'unknown')
            by_type[qtype] = by_type.get(qtype, 0) + 1
        
        print(f"\nBy type:")
        for qtype, count in sorted(by_type.items()):
            print(f"  {qtype}: {count} queries")
        
        # Estimate time
        est_time = self.estimate_execution_time(queries)
        print(f"\n⏱️ Estimated execution time: {est_time/60:.1f} minutes ({est_time/3600:.2f} hours)")
        print(f"{'='*60}")


if __name__ == "__main__":
    # Test with a sample configuration
    from config_handler import HazardConfig
    import json
    
    # Sample config
    sample_config = {
        "disaster_id": "2025-test-cyclone",
        "hazard_names": {
            "en": ["Test Cyclone"],
            "hi": ["परीक्षण चक्रवात"]
        },
        "keywords": {
            "en": ["flood", "rain", "damage", "rescue"],
            "hi": ["बाढ़", "बारिश", "क्षति"]
        },
        "locations": {
            "Test State": {
                "districts": {
                    "Test District": ["Test City"]
                }
            }
        },
        "newspapers": {
            "en": [{"name": "Test News", "link": "https://test.com"}]
        },
        "specific_links": [],
        "start_date": "01/01/2025",
        "end_date": "01/01/2025"
    }
    
    # Save and load
    with open('/tmp/test_config.json', 'w') as f:
        json.dump(sample_config, f)
    
    config = HazardConfig.from_json_file('/tmp/test_config.json')
    
    generator = QueryGenerator(config)
    
    # Generate smart queries
    queries = generator.generate_smart_queries(max_queries_per_lang=20)
    
    generator.print_query_summary(queries)
    
    # Show some sample queries
    print("\n📝 Sample queries:")
    for q in queries[:5]:
        print(f"  {q['lang_code']}: {q['query']} [{q['type']}]")