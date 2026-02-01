"""Test script for PSL fetcher with multiple indicators (async)."""

import asyncio
import yaml
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from climabc.fetchers import PSLFetcher


def load_config():
    """Load indicators configuration."""
    config_path = Path(__file__).parent / 'src' / 'climabc' / 'config' / 'indicators.yaml'
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


async def test_indicator(fetcher, indicator):
    """Test fetching a single indicator."""
    print(f"\n{'='*60}")
    print(f"Testing {indicator}")
    print('='*60)
    
    try:
        df = await fetcher.fetch(indicator)
        config = fetcher.get_indicator_config(indicator)
        
        print(f"✓ Successfully fetched {len(df)} records")
        print(f"  Name: {config.get('name')}")
        print(f"  Unit: {config.get('unit', 'N/A')}")
        print(f"  Category: {config.get('category')}")
        print(f"  Date range: {df['timestamp'].min().strftime('%Y-%m')} to {df['timestamp'].max().strftime('%Y-%m')}")
        print(f"  Value range: {df['value'].min():.2f} to {df['value'].max():.2f}")
        print(f"  Latest value: {df.iloc[-1]['value']:.2f} ({df.iloc[-1]['timestamp'].strftime('%Y-%m')})")
        
        return True
        
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_all_psl():
    """Test all PSL indicators."""
    print("Loading configuration...")
    config = load_config()
    
    print("Creating PSL fetcher...")
    
    async with PSLFetcher(config) as fetcher:
        indicators = fetcher.indicators
        print(f"\nFound {len(indicators)} indicators")
        print(f"Testing first 5: {', '.join(indicators[:5])}")
        
        results = {}
        for indicator in indicators[:5]:
            results[indicator] = await test_indicator(fetcher, indicator)
        
        print(f"\n{'='*60}")
        print("Summary")
        print('='*60)
        passed = sum(results.values())
        total = len(results)
        print(f"Passed: {passed}/{total}")
        
        for indicator, success in results.items():
            status = "✓" if success else "✗"
            print(f"  {status} {indicator}")


if __name__ == '__main__':
    asyncio.run(test_all_psl())
