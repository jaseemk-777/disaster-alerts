# Global Hazard News Extraction Pipeline

A flexible, configurable pipeline for extracting news articles about any type of natural disaster or hazard event from multiple sources and languages.

## 🌟 Features

- **Multi-language Support**: Extract news in any language with custom keywords
- **Hierarchical Location Filtering**: Search by country/state, district/parish, and city/village
- **Flexible Hazard Types**: Works for any disaster type (cyclones, floods, earthquakes, etc.)
- **Smart Query Generation**: Combines hazard names, keywords, locations, and news sources
- **Dual Search Strategy**:
  - Broad searches (hazard + keyword + location)
  - Targeted searches (hazard + keyword + location + newspaper)
- **Full Article Extraction**: Downloads complete article content, not just metadata
- **Intelligent Deduplication**: Removes duplicates across all dates and sources
- **Rate Limit Protection**: Smart delays and circuit breakers to avoid API bans

## 📋 Prerequisites

```bash
# Python 3.8+
pip install -r requirements.txt

# Install browser dependencies for Selenium/Playwright
playwright install
```

### Required Python Packages

```
pandas
pygooglenews
pytz
requests
beautifulsoup4
newspaper3k
selenium
playwright
trafilatura
psutil
webdriver-manager
```

## 🚀 Quick Start

### Option 1: Interactive Mode

```bash
python main_flexible.py --interactive
```

This will walk you through configuration step-by-step.

### Option 2: Configuration File

1. Create a JSON configuration file (see `example_config_cyclone_montha.json`)
2. Run the pipeline:

```bash
python main_flexible.py --config your_config.json
```

## 📝 Configuration Format

### Complete Configuration Structure

```json
{
  "disaster_id": "2025-cyclone-montha",
  "start_date": "01/11/2025",
  "end_date": "05/11/2025",
  "hazard_names": {
    "en": ["Cyclone Montha"],
    "hi": ["चक्रवात मोंथा"]
  },
  "keywords": {
    "en": ["flood", "rain", "damage", "rescue"],
    "hi": ["बाढ़", "बारिश", "नुकसान"]
  },
  "locations": {
    "Andhra Pradesh": {
      "districts": {
        "Visakhapatnam": ["Visakhapatnam City"],
        "East Godavari": ["Rajahmundry", "Kakinada"]
      }
    }
  },
  "newspapers": {
    "en": [
      {
        "name": "The Hindu",
        "link": "https://www.thehindu.com/"
      }
    ]
  },
  "specific_links": [
    "https://example.com/article1",
    "https://example.com/article2"
  ]
}
```

### Configuration Fields

#### Required Fields

- **disaster_id** (string): Unique identifier for the disaster (e.g., `"2025-cyclone-montha"`)
- **start_date** (string): Start date in DD/MM/YYYY format
- **end_date** (string): End date in DD/MM/YYYY format
- **hazard_names** (object): Hazard names in multiple languages

#### Optional Fields

- **keywords** (object): Search keywords by language (defaults to monsoon terms if not provided)
- **locations** (object): Hierarchical location structure (defaults to broad search if not provided)
- **newspapers** (object): News sources by language (optional, for targeted searches)
- **specific_links** (array): Specific article URLs to extract

### Example Configurations

#### Minimal Configuration

```json
{
  "disaster_id": "2025-example-disaster",
  "start_date": "01/01/2025",
  "end_date": "05/01/2025",
  "hazard_names": {
    "en": ["Example Disaster"]
  }
}
```

#### Global Earthquake Example

```json
{
  "disaster_id": "2025-turkey-syria-earthquake",
  "start_date": "06/02/2025",
  "end_date": "20/02/2025",
  "hazard_names": {
    "en": ["Turkey Syria Earthquake"],
    "tr": ["Türkiye Suriye Depremi"],
    "ar": ["زلزال تركيا سوريا"]
  },
  "keywords": {
    "en": ["earthquake", "collapsed building", "rescue", "casualties", "aftershock"],
    "tr": ["deprem", "yıkılan bina", "kurtarma", "can kaybı", "artçı sarsıntı"],
    "ar": ["زلزال", "مبنى منهار", "إنقاذ", "ضحايا", "هزة ارتدادية"]
  },
  "locations": {
    "Turkey": {
      "districts": {
        "Hatay": ["Antakya", "Iskenderun"],
        "Gaziantep": ["Gaziantep City"]
      }
    },
    "Syria": {
      "districts": {
        "Aleppo": ["Aleppo City"],
        "Latakia": ["Latakia City"]
      }
    }
  }
}
```

## 🎯 Usage Examples

### Basic Usage

```bash
# Interactive mode
python main_flexible.py --interactive

# Use configuration file
python main_flexible.py --config config.json
```

### Advanced Options

```bash
# Skip collection, only extract articles
python main_flexible.py --disaster-id 2025-cyclone-montha --extraction-only

# Skip extraction (only collect metadata)
python main_flexible.py --config config.json --skip-extraction

# Use more queries per language (may hit rate limits)
python main_flexible.py --config config.json --max-queries-per-lang 100

# Filter extraction by date range
python main_flexible.py --disaster-id 2025-cyclone-montha --extraction-only \
  --extraction-start-date 01/11/2025 --extraction-end-date 03/11/2025
```

### Running Individual Components

#### 1. News Collection Only

```python
from config_handler import HazardConfig
from hazard_news_collector import HazardNewsCollector

config = HazardConfig.from_json_file('config.json')
collector = HazardNewsCollector(config)
articles = collector.collect_all_news(use_smart_queries=True, max_queries_per_lang=50)
```

#### 2. Article Extraction Only

```python
from extract_articles_flexible import FlexibleArticleExtractor

extractor = FlexibleArticleExtractor('2025-cyclone-montha')
extractor.extract_all_articles()
```

## 📂 Output Structure

```
project/
├── data/
│   └── 2025-cyclone-montha/           # Disaster-specific folder
│       └── 2025/
│           └── 11/
│               ├── 01/
│               │   └── results.csv    # Metadata for Nov 1
│               ├── 02/
│               │   └── results.csv    # Metadata for Nov 2
│               └── ...
├── JSON Output/
│   └── 2025-cyclone-montha/
│       └── articles_combined.json     # High + medium quality articles
└── JSON Output Spare/
    └── 2025-cyclone-montha/
        ├── articles_all.json          # All articles
        ├── articles_high_quality.json # High quality only
        ├── articles_medium_quality.json
        ├── articles_low_quality.json
        └── extraction_stats.json      # Statistics
```

## 🔍 Query Generation Logic

The pipeline generates two types of queries:

### 1. Broad Queries (without news source)

Format: `{hazard} {keyword} {location} {year}`

Example: `"Cyclone Montha flood Visakhapatnam 2025"`

### 2. Targeted Queries (with news source)

Format: `{hazard} {keyword} {location} {newspaper} {year}`

Example: `"Cyclone Montha flood Visakhapatnam Eenadu 2025"`

### Smart Query Limiting

To avoid rate limits, the pipeline uses intelligent query limiting:

- **Broad Priority** (25% of budget): Hazard + Top Keywords
- **Location Priority** (40% of budget): Hazard + Keyword + Major Locations
- **Newspaper Priority** (35% of budget): Hazard + Keyword + Location + Newspaper

Default: 50 queries per language (adjustable with `--max-queries-per-lang`)

## 🛡️ Rate Limiting Protection

The pipeline includes several rate limiting protections:

1. **Adaptive Delays**: Increases delay time after failures
2. **Circuit Breaker**: Stops queries after consecutive failures
3. **Query Pattern Learning**: Learns which patterns succeed/fail
4. **Inter-language Delays**: Longer delays between languages
5. **Batch Processing**: Processes articles in small batches

## 📊 Article Quality Assessment

Articles are automatically classified as:

- **High Quality**: >1500 chars, 3+ paragraphs, good word diversity, no HTML artifacts
- **Medium Quality**: >500 chars, 2+ paragraphs, reasonable diversity
- **Low Quality**: Everything else

## 🔄 Deduplication Strategy

The pipeline performs multi-stage deduplication:

1. **URL Normalization**: Removes tracking parameters, handles redirects
2. **Content Fingerprinting**: Checks for identical content
3. **Cross-date Deduplication**: Removes duplicates across all dates
4. **Quality-based Selection**: Keeps higher quality version when duplicates found

## 🌐 Language Support

### Supported Languages (with built-in keywords)

- English (en)
- Hindi (hi)
- Telugu (te)
- Tamil (ta)
- Malayalam (ml)
- Kannada (kn)
- Bengali (bn)
- Gujarati (gu)
- Marathi (mr)
- Odia (or)
- Punjabi (pa)
- Assamese (as)

### Adding New Languages

Simply provide hazard names and keywords in your configuration:

```json
{
  "hazard_names": {
    "fr": ["Cyclone Montha"]
  },
  "keywords": {
    "fr": ["inondation", "pluie", "dommages", "sauvetage"]
  }
}
```

## 🐛 Troubleshooting

### Rate Limiting Errors

If you encounter rate limiting:

1. Reduce `--max-queries-per-lang` (try 20-30)
2. Use `--skip-collection` and run extraction separately
3. Add delays in `smart_google_news_handler.py`

### ChromeDriver Issues

```bash
# Update ChromeDriver
pip install --upgrade webdriver-manager

# Or use system ChromeDriver
export CHROME_BIN=/path/to/chrome
```

### No Articles Extracted

1. Check date range is correct (DD/MM/YYYY format)
2. Verify locations and keywords are relevant
3. Try broader searches (remove location filtering)
4. Check logs for specific errors

### Memory Issues

For large extractions:

1. Process smaller date ranges
2. Reduce parallelism in `ArticleScraper`
3. Use `--extraction-only` mode separately

## 📈 Performance Tips

### For Fast Collection

```bash
python main_flexible.py --config config.json \
  --max-queries-per-lang 30 \
  --skip-extraction
```

Then run extraction separately in batches.

### For Comprehensive Coverage

```bash
python main_flexible.py --config config.json \
  --max-queries-per-lang 100 \
  --use-all-queries
```

⚠️ Warning: May trigger rate limits

### For Production Use

1. Save configuration files for repeatability
2. Use moderate query limits (40-60)
3. Monitor logs for errors
4. Run extraction separately during off-peak hours

## 🤝 Contributing

Contributions welcome! Areas for improvement:

- Additional language support
- More news source integrations
- Better content extraction algorithms
- Enhanced deduplication logic
- Performance optimizations

## 📄 License

MIT License - feel free to use and modify

## 📞 Support

For issues or questions:
1. Check logs in console output
2. Review configuration format
3. Try example configurations
4. Check rate limiting status

## 🔮 Future Enhancements

- [ ] Multi-country Google News support
- [ ] Social media integration
- [ ] Real-time monitoring mode
- [ ] API endpoint for programmatic access
- [ ] Dashboard for results visualization
- [ ] Automatic language detection
- [ ] Machine learning for relevance filtering