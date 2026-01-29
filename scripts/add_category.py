#!/usr/bin/env python3
"""
Add category field to all .pattern files based on existing tags.

Category mapping (based on BANK_TAGS):
- Ambient: ambient, wave, chill, slow
- Buildup: energy, flash, chase, build
- Chill: classic, rainbow, pulse, fade
- Upbeat: strobe, spatial, signature, fast
"""

from pathlib import Path

BANK_TAGS = {
    'Ambient': ['ambient', 'wave', 'chill', 'slow'],
    'Buildup': ['energy', 'flash', 'chase', 'build'],
    'Chill': ['classic', 'rainbow', 'pulse', 'fade'],
    'Upbeat': ['strobe', 'spatial', 'signature', 'fast'],
}

def determine_category(tags: list[str]) -> str:
    """Determine category from tags. Returns first matching category or 'Chill' as default."""
    tags_lower = [t.lower() for t in tags]

    for category, category_tags in BANK_TAGS.items():
        for tag in category_tags:
            if tag in tags_lower:
                return category

    # Default to Chill if no match
    return 'Chill'

def migrate_pattern_file(file_path: Path) -> tuple[str, str]:
    """Add category to a pattern file. Returns (name, category)."""
    text = file_path.read_text()

    if '---' not in text:
        raise ValueError(f"Missing '---' separator in {file_path}")

    header_text, body = text.split('---', 1)

    # Parse header
    name = ""
    tags = []
    has_category = False

    for line in header_text.strip().split('\n'):
        line = line.strip()
        if not line or ':' not in line:
            continue
        key, value = line.split(':', 1)
        key = key.strip().lower()
        value = value.strip()

        if key == 'name':
            name = value
        elif key == 'tags':
            tags = [t.strip() for t in value.split(',') if t.strip()]
        elif key == 'category':
            has_category = True

    if has_category:
        print(f"  Skipping {file_path.name} (already has category)")
        return name, ""

    category = determine_category(tags)

    # Insert category line after name line
    new_lines = []
    for line in header_text.strip().split('\n'):
        new_lines.append(line)
        stripped = line.strip()
        if stripped.startswith('name:'):
            new_lines.append(f"category: {category}")

    new_header = '\n'.join(new_lines)
    new_content = f"{new_header}\n---{body}"

    file_path.write_text(new_content)
    return name, category

def main():
    patterns_dir = Path(__file__).parent.parent / 'patterns'

    if not patterns_dir.exists():
        print(f"Patterns directory not found: {patterns_dir}")
        return

    pattern_files = sorted(patterns_dir.glob('*.pattern'))
    print(f"Found {len(pattern_files)} pattern files\n")

    categories_count = {'Ambient': 0, 'Buildup': 0, 'Chill': 0, 'Upbeat': 0}

    for file_path in pattern_files:
        try:
            name, category = migrate_pattern_file(file_path)
            if category:
                print(f"  {file_path.name}: {category}")
                categories_count[category] += 1
        except Exception as e:
            print(f"  Error in {file_path.name}: {e}")

    print(f"\nMigration complete!")
    print("Category distribution:")
    for cat, count in categories_count.items():
        print(f"  {cat}: {count}")

if __name__ == '__main__':
    main()
