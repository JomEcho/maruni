# 🎓 Leerdoel Extractor

**Extract learning objectives from PDF study materials** using AI (OpenAI/Anthropic).

Converts your textbooks, articles, and study materials into structured learning objectives that you can import into jomuni for practice.

## ✨ What it does

1. **📄 Reads PDF** - Extracts all text from your study material
2. **🤖 AI Analysis** - Uses LLM to identify key learning objectives
3. **📝 Structured Output** - Generates both Markdown and JSON files
4. **🎯 Ready for Practice** - Import into jomuni to start learning

## 🚀 Quick Start

### 1. Setup

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure API keys
cp .env.example .env
nano .env  # Add your OpenAI or Anthropic API key
```

### 2. Extract Learning Objectives

```bash
# Basic usage
./extract.py your_textbook.pdf

# Specify output directory
./extract.py statistics_ch3.pdf --output-dir learning-objectives/statistics

# Add domain/subject
./extract.py physics_book.pdf --domain PHYS
```

### 3. Import into jomuni

The generated files can be imported into jomuni:
- `{filename}_leerdoelen.json` - Structured data for import
- `{filename}_leerdoelen.md` - Human-readable overview

## 📋 Output Format

### Markdown Example
```markdown
---
generated_at: 2025-08-09T10:30:00
source: statistics_ch3.pdf
count: 12
domains: STAT
---

# Leerdoelen: statistics_ch3

## STAT

### 1. P-value interpretatie
**Bloom niveau:** understand
**Samenvatting:** Begrijp wat een p-value betekent en hoe je deze interpreteert...

### 2. Central Limit Theorem toepassen
**Bloom niveau:** apply
**Samenvatting:** Pas het CLT toe om de verdeling van steekproefgemiddelden te bepalen...
```

### JSON Example
```json
{
  "generated_at": "2025-08-09T10:30:00",
  "count": 12,
  "learning_objectives": [
    {
      "concept": "P-value interpretatie",
      "bloom": "understand",
      "summary": "Begrijp wat een p-value betekent...",
      "domain": "STAT"
    },
    ...
  ]
}
```

## ⚙️ Configuration

Edit `.env` to configure:

```bash
# LLM Provider (openai or anthropic)
LLM_PROVIDER=openai

# Model
MODEL_NAME=gpt-4o-mini

# API Keys
OPENAI_API_KEY=your_key_here
# ANTHROPIC_API_KEY=your_key_here
```

## 🎯 Bloom Taxonomy Levels

The extractor categorizes learning objectives using Bloom's taxonomy:
- **remember** - Recall facts and basic concepts
- **understand** - Explain ideas or concepts
- **apply** - Use information in new situations
- **analyze** - Draw connections among ideas
- **evaluate** - Justify a decision or course of action
- **create** - Produce new or original work

## 📁 Project Structure

```
leerdoel-extractor/
├── extract.py              # Main CLI script
├── core/
│   ├── llm.py             # LLM client (OpenAI/Anthropic)
│   ├── profile.py         # Learner profile loader
│   └── settings.py        # Configuration
├── config/
│   └── learner_profile.yaml  # Your learning preferences
├── output/                # Default output directory
│   ├── *.json            # Generated JSON files
│   └── *.md              # Generated Markdown files
└── README.md
```

## 🔧 Advanced Usage

### Process Multiple PDFs

```bash
# Process all PDFs in a directory
for pdf in books/*.pdf; do
  ./extract.py "$pdf" --output-dir learning-objectives/$(basename "$pdf" .pdf)
done
```

### Custom Output Location

```bash
# Organize by subject
./extract.py statistics.pdf --output-dir learning-objectives/statistics --domain STAT
./extract.py physics.pdf --output-dir learning-objectives/physics --domain PHYS
./extract.py finance.pdf --output-dir learning-objectives/finance --domain FIN
```

## 💡 Tips

- **Chunk Processing**: The extractor processes large PDFs in chunks (first 5 chunks max)
- **API Costs**: Uses ~$0.01-0.05 per PDF depending on length
- **Quality**: Works best with well-structured textbooks and academic papers
- **Language**: Optimized for Dutch output based on learner profile

## 🔗 Integration with jomuni

After extracting learning objectives:

1. Open jomuni
2. Go to "Import Leerdoelen" (to be implemented)
3. Select the generated JSON file
4. Start practicing!

## 🛠️ Requirements

- Python 3.9+
- OpenAI API key OR Anthropic API key
- PyMuPDF (for PDF reading)
- Internet connection (for LLM API calls)

## 📝 License

MIT - Use this tool to learn and grow! 🌱
