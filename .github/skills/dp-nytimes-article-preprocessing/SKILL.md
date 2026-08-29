---
name: dp-nytimes-article-preprocessing
description: Process a NYTimes article source JSON and an article content text file to generate a learner-friendly article JSON file.
---
# Article JSON Generation Skill

## Purpose
Generate a learner-friendly article JSON file from two inputs:
- an article source JSON file
- an article content text file

The output should be a JSON file with the structure expected by the reading-list app.

---

## Input Handling
When this skill runs, it should first check whether the required files are already available.

If both files are present, use them directly.
If either file is missing, ask the user to provide the missing input before generating the JSON.

The skill should not assume hard-coded file names or hard-coded locations.

### Required inputs
1. A source metadata JSON file containing article metadata such as title, abstract, image URLs, and source information.
2. An article content text file containing the article body.

### If files are missing
Ask the user for:
- the source JSON file path or content
- the article text file path or content

If the user provides only one of the two, wait for the other before continuing.

The generated output file should be named articleOutput.json unless the user specifies a different name.

---

## Expected Output JSON Format

```json
{
  "id": "1",
  "title": "Article title",
  "summary": "Chinese summary of the reading summary",
  "readingSummary": "Simple English summary for learners",
  "difficulty": "B2",
  "duration": "4 min",
  "tags": ["健康", "医学"],
  "thumbLarge": "https://example.com/image.jpg",
  "superJumbo": "https://example.com/image.jpg",
  "questions": [
    {
      "id": "q1",
      "question": "What is the main idea of the article?",
      "answer": "The main idea is that..."
    }
  ],
  "content": {
    "paragraphs": [
      {
        "id": "p1",
        "text": "This is the first sentence. This is the second sentence.",
        "translation": "Chinese translation of paragraph",
        "sentences": [
          {
            "id": "s1",
            "text": "This is the first sentence. ",
            "translation": "这是第一句",
            "audio": "/audio/s1.mp3",
            "words": [
              {
                "word": "sentence",
                "phonetic": "/ˈwɜːd/",
                "meaning": "句子",
                "example": "Example sentence"
              }
            ]
          },
          {
            "id": "s2",
            "text": "This is the second sentence. ",
            "translation": "这是第二句",
            "audio": "/audio/s2.mp3",
            "words": [
              {
                "word": "sentence",
                "phonetic": "/ˈwɜːd/",
                "meaning": "句子",
                "example": "Example sentence"
              }
            ]
          }
        ]
      }
    ]
  }
}
```

---

## Field Specification

### 1. id
- Type: string
- Value: a stable article identifier, usually "1", "2", or derived from the source file.
- Generation rule: use a simple incremental ID if no ID exists.

### 2. title
- Type: string
- Value: the article title.
- Generation rule: take the title from articleSource.json, preferably from headline.main or the closest available title field.

### 3. summary
- Type: string
- Value: a Chinese summary of the reading summary.
- Generation rule: translate the readingSummary into concise Chinese.

### 4. readingSummary
- Type: string
- Value: a short, simple English summary of the article for language learners.
- Generation rule:
  - use simple words and short sentences
  - keep it under 60 words
  - capture the main idea and why it matters
  - make it intriguing enough to encourage reading
- Good style: clear, plain English, not too academic.

### 5. difficulty
- Type: string
- Value: CEFR-style level such as A2, B1, B2, C1.
- Generation rule:
  - choose the level based on the article's vocabulary and sentence complexity
  - use B1 or B2 for most news/editorial articles
  - use A2 for very easy articles and C1 for highly advanced ones

### 6. duration
- Type: string
- Value: a rough listening/reading time estimate.
- Generation rule:
  - use a compact format such as "3 min", "4 min", or "5 min"
  - estimate based on article length and reading difficulty

### 7. tags
- Type: array of strings
- Value: topic labels.
- Generation rule:
  - choose 2 to 4 short tags
  - use common topic labels such as health, science, education, technology, psychology, society, politics
  - prefer simple, useful tags rather than overly specific ones

### 8. thumbLarge
- Type: string
- Value: image URL for a small preview image.
- Generation rule: use the article image URL from articleSource.json if available; otherwise leave empty or use a reasonable fallback.

### 9. superJumbo
- Type: string
- Value: large image URL.
- Generation rule: use the largest available image URL from articleSource.json if present.

### 10. questions
- Type: array of objects
- Value: one or two simple intriguing questions and answers about the article for language learners. They will read questions before listening to the article.
- Generation rule: 
  - create 1 to 2 questions that are relevant to the article content
  - keep questions simple and clear
  - provide concise answers that are accurate and easy to understand

### 10. content.paragraphs
- Type: array
- Value: article content divided into paragraphs.
- Generation rule:
  - split the text into paragraphs based on blank lines or clear paragraph boundaries
  - preserve the original wording as much as possible
  - create one paragraph object per paragraph

### 11. paragraphs[].id
- Type: string
- Value: paragraph identifier.
- Generation rule: use p1, p2, p3, and so on.

### 12. paragraphs[].text
- Type: string
- Value: the original paragraph text.
- Generation rule: copy the paragraph from the article content file with minimal editing.

### 13. paragraphs[].translation
- Type: string
- Value: Chinese translation of the paragraph.
- Generation rule: translate the paragraph naturally into Chinese, keeping the meaning accurate.

### 14. paragraphs[].sentences
- Type: array
- Value: a list of sentences from the paragraph.
- Generation rule:
  - split the paragraph into sentences
  - create one sentence object per sentence
  - keep the original English sentence text intact
  - make sure all the sentences are included in the order they appear in the paragraph

### 15. sentences[].id
- Type: string
- Value: sentence identifier.
- Generation rule: use s1, s2, s3, and so on in sequence.

### 16. sentences[].text
- Type: string
- Value: original sentence text.
- Generation rule: preserve the sentence exactly or with minimal cleanup.

### 17. sentences[].translation
- Type: string
- Value: Chinese translation of the sentence.
- Generation rule: provide a clear, natural translation.

### 18. sentences[].audio
- Type: string
- Value: placeholder audio path.
- Generation rule: use a simple placeholder such as /audio/s1.mp3, /audio/s2.mp3, and so on.

### 19. sentences[].words
- Type: array
- Value: vocabulary or useful phrase items worth learning.
- Generation rule:
  - choose useful, common, and learner-friendly words or chunks
  - avoid obscure or overly rare terms
  - prefer words that are likely to help learners understand the article
  - include 1 to 4 items per sentence if appropriate

### 20. words[].word
- Type: string
- Value: vocabulary item or phrase.
- Generation rule: use a real word, phrase, or chunk from the sentence.

### 21. words[].phonetic
- Type: string
- Value: pronunciation guide.
- Generation rule: use a simple phonetic representation, such as /ˈwɜːd/.

### 22. words[].meaning
- Type: string
- Value: Chinese meaning.
- Generation rule: provide a concise and clear translation.

### 23. words[].example
- Type: string
- Value: a short example sentence using the word or phrase.
- Generation rule: create a simple example that is easy for learners to understand.

---

## LLM Generation Guidance

When generating the JSON, the model should:
1. Read the article source JSON carefully for metadata such as title, image URLs, and abstract.
2. Read the article content text file for the main body.
3. Keep the original article meaning accurate.
4. Write the readingSummary in simple English with clear meaning.
5. Translate that summary into Chinese for summary.
6. Choose a realistic CEFR difficulty level.
7. Split the content into paragraph and sentence-level units.
8. Add useful vocabulary items that are relevant and practical for learners.
9. Avoid inventing information not present in the source text.
10. Keep the JSON valid and consistent.

---

## Quality Rules
- Do not invent facts not present in the article.
- Do not use overly advanced or rare vocabulary in the readingSummary.
- Keep the readingSummary short and engaging.
- Use simple and practical vocabulary for the word list.
- Keep translations natural and clear.
- Preserve the article’s core meaning.

---

## Recommended Prompt

Use the following instruction with the two files in place:

"Generate a learner-friendly article JSON file from the provided article source JSON and article content text. Use the title, image URLs, and metadata from the source JSON. Use the article body from the text file. Create a simple English reading summary, a Chinese summary, an appropriate CEFR difficulty level, a short duration estimate, topic tags, and structured paragraph/sentence content with translations and vocabulary items. Output valid JSON only."

---

## Output File
- Output path: articleOutput.json
- If the file already exists, overwrite it with the newly generated content.
