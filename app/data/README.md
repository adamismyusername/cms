# Auto-Tag Keywords Data

## CSV File Location

Place your auto-tag keyword mappings CSV file here as:
`auto-tag-keywords.csv`

## CSV Format

The CSV should have two columns:
- `keyword` - The keyword or phrase to match in quote text
- `tags` - Comma-separated list of tags to apply when keyword is found

## Example CSV Content

```csv
keyword,tags
gold,"gold, precious metals"
inflation,"inflation, economy"
trump,"donald trump, politics"
federal reserve,"federal reserve, monetary policy"
stock market,"stock market, investing"
```

## Notes

- Keywords are matched case-insensitively
- Whole-word matching is used (e.g., "gold" won't match "golden")
- Multi-word keywords are supported (e.g., "stock market")
- After updating the CSV, use the admin panel to reload keywords or restart the app
