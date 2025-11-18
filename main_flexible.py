"""
Main Flexible Hazard News Extraction Pipeline
Orchestrates the entire workflow for any hazard type and location
"""

import argparse
import sys
import os
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)


def main():
    """Main pipeline orchestrator"""
    parser = argparse.ArgumentParser(
        description='Global Hazard News Extraction Pipeline',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive mode - walk through configuration step-by-step
  python main_flexible.py --interactive
  
  # Load from configuration file
  python main_flexible.py --config config_2025-cyclone-montha.json
  
  # Skip extraction step (only collect metadata)
  python main_flexible.py --config myconfig.json --skip-extraction
  
  # Only run extraction on existing data
  python main_flexible.py --disaster-id 2025-cyclone-montha --extraction-only
        """
    )
    
    # Configuration input methods
    config_group = parser.add_mutually_exclusive_group(required=True)
    config_group.add_argument('--interactive', action='store_true',
                             help='Interactive configuration input')
    config_group.add_argument('--config', type=str,
                             help='Path to JSON configuration file')
    config_group.add_argument('--disaster-id', type=str,
                             help='Disaster ID (for extraction-only mode)')
    
    # Pipeline control
    parser.add_argument('--skip-collection', action='store_true',
                       help='Skip news collection step')
    parser.add_argument('--skip-extraction', action='store_true',
                       help='Skip article extraction step')
    parser.add_argument('--extraction-only', action='store_true',
                       help='Only run extraction (requires existing data)')
    
    # Collection parameters
    parser.add_argument('--max-queries-per-lang', type=int, default=50,
                       help='Maximum queries per language (default: 50)')
    parser.add_argument('--use-all-queries', action='store_true',
                       help='Use all generated queries (not recommended, may hit rate limits)')
    
    # Extraction parameters
    parser.add_argument('--extraction-start-date', type=str,
                       help='Filter extraction by start date (DD/MM/YYYY)')
    parser.add_argument('--extraction-end-date', type=str,
                       help='Filter extraction by end date (DD/MM/YYYY)')
    
    args = parser.parse_args()
    
    logger = logging.getLogger(__name__)
    
    print("\n" + "="*80)
    print("🌍 GLOBAL HAZARD NEWS EXTRACTION PIPELINE")
    print("="*80)
    
    try:
        # Step 0: Load or create configuration
        config = None
        
        if args.extraction_only:
            if not args.disaster_id:
                print("❌ --disaster-id required for extraction-only mode")
                sys.exit(1)
            
            disaster_id = args.disaster_id
            logger.info(f"Running in extraction-only mode for disaster: {disaster_id}")
        
        elif args.interactive:
            logger.info("Starting interactive configuration...")
            from config_handler import load_config_interactive
            config = load_config_interactive()
            disaster_id = config.disaster_id
        
        elif args.config:
            if not os.path.exists(args.config):
                print(f"❌ Configuration file not found: {args.config}")
                sys.exit(1)
            
            logger.info(f"Loading configuration from: {args.config}")
            from config_handler import HazardConfig
            config = HazardConfig.from_json_file(args.config)
            
            if not config.validate():
                print("❌ Invalid configuration")
                sys.exit(1)
            
            config.print_summary()
            disaster_id = config.disaster_id
        
        # Step 1: News Collection
        if not args.skip_collection and not args.extraction_only:
            logger.info("\n" + "="*80)
            logger.info("STEP 1: NEWS COLLECTION")
            logger.info("="*80)
            
            from hazard_news_collector import HazardNewsCollector
            
            collector = HazardNewsCollector(config)
            
            articles = collector.collect_all_news(
                use_smart_queries=not args.use_all_queries,
                max_queries_per_lang=args.max_queries_per_lang
            )
            
            logger.info(f"✅ News collection complete: {len(articles)} articles collected")
        
        elif args.skip_collection:
            logger.info("\n⏭️ Skipping news collection step")
        
        # Step 2: Article Extraction
        if not args.skip_extraction:
            logger.info("\n" + "="*80)
            logger.info("STEP 2: FULL ARTICLE CONTENT EXTRACTION")
            logger.info("="*80)
            
            from extract_articles_flexible import FlexibleArticleExtractor
            
            # Parse extraction date range if provided
            extraction_date_range = None
            if args.extraction_start_date and args.extraction_end_date:
                try:
                    start_date = datetime.strptime(args.extraction_start_date, '%d/%m/%Y').date()
                    end_date = datetime.strptime(args.extraction_end_date, '%d/%m/%Y').date()
                    extraction_date_range = (start_date, end_date)
                    logger.info(f"Filtering extraction: {start_date} to {end_date}")
                except ValueError:
                    logger.error("Invalid date format for extraction dates. Use DD/MM/YYYY")
                    sys.exit(1)
            
            extractor = FlexibleArticleExtractor(disaster_id)
            extractor.extract_all_articles(extraction_date_range)
            
            logger.info("✅ Article extraction complete")
        
        elif args.skip_extraction:
            logger.info("\n⏭️ Skipping article extraction step")
        
        # Final summary
        print("\n" + "="*80)
        print("🎉 PIPELINE COMPLETE")
        print("="*80)
        print(f"\n📁 Disaster ID: {disaster_id}")
        print(f"📂 Data location: data/{disaster_id}/")
        print(f"📂 JSON output: JSON Output/{disaster_id}/")
        print(f"📂 Detailed output: JSON Output Spare/{disaster_id}/")
        print("\n" + "="*80)
        
    except KeyboardInterrupt:
        print("\n\n⚠️ Pipeline interrupted by user")
        sys.exit(1)
    
    except Exception as e:
        logger.error(f"❌ Pipeline error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()